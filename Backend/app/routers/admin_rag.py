"""
TUH Chatbot AI — Admin Router: RAG Teaching (ทดสอบค้นหา + สอนบอทผ่านเอกสาร)

ใช้จากหน้าคำถามที่บอทตอบไม่ได้ เมื่อแอดมินยืนยันว่าเอกสารมีคำตอบอยู่แล้ว:
  1. POST /rag/test-search        ค้นด้วย HybridRetriever ตรงๆ (ไม่เรียก LLM, ไม่บันทึกประวัติ/unanswered)
                                  ดูว่า chunk ที่มีคำตอบติดอันดับที่ส่งให้บอทหรือไม่
  2. POST /rag/chunks/search      ค้นหา chunk ด้วยข้อความ กรณีไม่ติดอันดับในข้อ 1 เลย
  3. POST /rag/chunk-hints/suggest  ให้ LLM เสนอคำถามตัวอย่างของ chunk ที่เลือก
  4. PUT  /rag/chunk-hints        บันทึกคำถามตัวอย่าง → นำเข้าดัชนีทันที → ค้นซ้ำเพื่อยืนยันผล
"""
import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.models import ChunkHint, SystemSettings, User
from app.schemas.schemas import (
    ChunkHintSave, ChunkHintSuggestRequest, RagChunkSearchRequest, RagTestSearchRequest,
)
from app.services import chunk_hint_service as hint_svc
from app.services.rag_service import get_retriever

router = APIRouter(prefix="/api/admin/rag", tags=["admin"])

SEARCH_DEPTH = 10  # แสดงลึกกว่า top_k ที่ส่งให้ LLM เพื่อให้เห็นว่า chunk ที่ถูกต้องอยู่อันดับไหน


def _require_retriever():
    retriever = get_retriever()
    if retriever is None or not getattr(retriever, "is_loaded", False):
        raise HTTPException(status_code=503, detail="ระบบค้นหายังไม่พร้อมใช้งาน (ยังไม่ได้โหลดดัชนี)")
    return retriever


async def _settings_row(db: AsyncSession) -> Optional[SystemSettings]:
    return (await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))).scalar_one_or_none()


async def _all_hints(db: AsyncSession):
    return hint_svc.hints_map((await db.execute(select(ChunkHint))).scalars().all())


async def _search(retriever, query: str, depth: int = SEARCH_DEPTH):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: retriever.query(query, top_k=depth))


@router.post("/test-search")
async def test_search(
    body: RagTestSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    retriever = _require_retriever()
    cfg = await _settings_row(db)
    top_k = cfg.top_k if cfg and cfg.top_k else 3
    results = await _search(retriever, body.query.strip())
    hints = await _all_hints(db)
    emb = hint_svc._admin_module()
    return {
        "top_k": top_k,
        "dense_enabled": bool(getattr(retriever, "dense_enabled", False)),
        "results": [
            {
                **hint_svc.serialize_chunk(r, emb, hints),
                "rank": r.get("hybrid_rank"),
                "in_chat_context": (r.get("hybrid_rank") or 99) <= top_k,
                "dense_rank": r.get("dense_rank"),
                "dense_score": r.get("dense_score"),
                "lexical_rank": r.get("lexical_rank"),
            }
            for r in results
        ],
    }


@router.post("/chunks/search")
async def search_chunks(
    body: RagChunkSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    retriever = _require_retriever()
    keyword = body.keyword.strip().lower()
    hints = await _all_hints(db)
    emb = hint_svc._admin_module()
    matches = []
    for c in retriever.bm25_chunks or []:
        meta = c.get("metadata") or {}
        if body.source and meta.get("source") != body.source:
            continue
        if keyword in (c.get("content") or "").lower():
            matches.append(hint_svc.serialize_chunk(c, emb, hints))
            if len(matches) >= 20:
                break
    return {"results": matches}


@router.post("/chunk-hints/suggest")
async def suggest_hint_questions(
    body: ChunkHintSuggestRequest,
    current_user: User = Depends(get_current_user),
):
    retriever = _require_retriever()
    chunk = hint_svc.find_chunk(retriever, body.source, body.chunk_hash)
    if not chunk:
        raise HTTPException(status_code=404, detail="ไม่พบส่วนย่อยเอกสารนี้ในดัชนีปัจจุบัน")
    return {"questions": await hint_svc.suggest_questions(chunk.get("content", ""), body.query.strip())}


@router.get("/chunk-hints")
async def list_chunk_hints(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    retriever = get_retriever()
    rows = (await db.execute(select(ChunkHint).order_by(ChunkHint.updated_at.desc()))).scalars().all()
    return [
        {
            "id": h.id,
            "source": h.source,
            "page": h.page,
            "chunk_hash": h.chunk_hash,
            "content_preview": h.content_preview,
            "questions": json.loads(h.questions or "[]"),
            "unanswered_id": h.unanswered_id,
            # ไม่เจอ chunk ในดัชนีปัจจุบัน = เอกสารถูกลบ/อัปโหลดใหม่จนเนื้อหาเปลี่ยน hint จึงไม่มีผลแล้ว
            "active": bool(retriever and hint_svc.find_chunk(retriever, h.source, h.chunk_hash)),
        }
        for h in rows
    ]


@router.put("/chunk-hints")
async def save_chunk_hint(
    body: ChunkHintSave,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    retriever = _require_retriever()
    cfg = await _settings_row(db)
    if cfg and cfg.rebuild_status == "processing":
        raise HTTPException(status_code=409, detail="ระบบกำลังสร้างดัชนีใหม่อยู่ กรุณารอสักครู่แล้วลองอีกครั้ง")

    chunk = hint_svc.find_chunk(retriever, body.source, body.chunk_hash)
    if not chunk:
        raise HTTPException(status_code=404, detail="ไม่พบส่วนย่อยเอกสารนี้ในดัชนีปัจจุบัน")
    questions = hint_svc.clean_questions(body.questions)

    hint = (await db.execute(
        select(ChunkHint).where(ChunkHint.source == body.source, ChunkHint.chunk_hash == body.chunk_hash)
    )).scalar_one_or_none()
    if hint is None:
        hint = ChunkHint(source=body.source, chunk_hash=body.chunk_hash, created_by_id=current_user.id)
        db.add(hint)
    hint.page = (chunk.get("metadata") or {}).get("page")
    hint.content_preview = chunk.get("content", "")
    hint.questions = json.dumps(questions, ensure_ascii=False)
    if body.unanswered_id:
        hint.unanswered_id = body.unanswered_id
    await db.commit()
    await db.refresh(hint)

    hints = await _all_hints(db)
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, hint_svc.apply_hints_sync, hints)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"บันทึกคำถามแล้ว แต่นำเข้าดัชนีค้นหาไม่สำเร็จ: {e}")

    verification = None
    verify_query = (body.verify_query or "").strip()
    if verify_query:
        top_k = cfg.top_k if cfg and cfg.top_k else 3
        rank = hint_svc.rank_of_chunk(await _search(retriever, verify_query), body.source, body.chunk_hash)
        verification = {"query": verify_query, "rank": rank, "top_k": top_k,
                        "in_chat_context": rank is not None and rank <= top_k}

    return {"id": hint.id, "questions": questions, "verification": verification}


@router.delete("/chunk-hints/{hint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chunk_hint(
    hint_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    hint = (await db.execute(select(ChunkHint).where(ChunkHint.id == hint_id))).scalar_one_or_none()
    if not hint:
        raise HTTPException(status_code=404, detail="ไม่พบรายการนี้")
    await db.delete(hint)
    await db.commit()
    if get_retriever() is not None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, hint_svc.apply_hints_sync, await _all_hints(db))
