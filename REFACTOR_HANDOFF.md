# TUH Chatbot AI — Cleanup Refactor: Handoff Document

**เขียนไว้เผื่อกรณีต้องส่งต่องานให้ AI agent ตัวอื่น (เช่น Antigravity) ทำต่อ หากเซสชันนี้
token หมดก่อนงานเสร็จ** — เอกสารนี้สรุปสถานะล่าสุด + รายละเอียดที่ต้องรู้เพื่อทำต่อได้ทันที
โดยไม่ต้องเดา

อัปเดตล่าสุด: 2026-09-22

## เป้าหมายรวม

ผู้ใช้ (นักศึกษาฝึกงาน) กำลังจะส่งต่อโค้ด TUH Chatbot AI นี้ให้แผนกไอทีของโรงพยาบาล
จึงต้องจัดระเบียบโค้ดให้แยกสัดส่วนชัดเจนก่อนส่งมอบ งานคือ **แยกไฟล์ตาม domain +
ดึง business logic ออกจาก route handler/component body ไปเป็น service/hook layer**
ทั้ง Backend + UserWeb + AdminWeb โดย **ห้ามเปลี่ยนพฤติกรรมใดๆ เลย** (ไม่ใช่ feature
เปลี่ยนแปลง ไม่ใช่ UI เปลี่ยนแปลง โดยเฉพาะ UserWeb ที่ UI/พฤติกรรมถูกล็อกไว้ตามกฎ
โปรเจกต์ — ดู `CLAUDE.md` ที่ root ข้อ 3)

แผนฉบับเต็มที่ผู้ใช้อนุมัติแล้วอยู่ที่ (เฉพาะเครื่องนี้ ในเครื่องอื่นอาจไม่มี):
`C:\Users\ITS\.claude\plans\mutable-crafting-bengio.md`
— ถ้าเข้าถึงไฟล์นั้นไม่ได้ (เช่นเปิดจากเครื่อง/tool อื่น) ให้ใช้เอกสารนี้แทนเป็นแหล่งความจริง
สำหรับส่วนที่เหลือ (Phase U) เพราะคัดลอกรายละเอียดสำคัญมาไว้ครบด้านล่างแล้ว

ลำดับที่วางไว้ (เรียงตามความเสี่ยง): **B1 → B2 → A → U**

## สถานะปัจจุบัน (เช็คด้วยตัวเองก่อนเชื่อ — ดูหัวข้อ "วิธีตรวจสอบสถานะจริง" ด้านล่าง)

| Phase | เนื้อหา | สถานะ |
|---|---|---|
| B1 | Backend: Feedback, Unanswered, Stats, Forms, Announcements, History, Auth (login/password) แยกออกจาก `admin.py` | ✅ เสร็จ + ตรวจสอบแล้ว |
| B2 | Backend: Documents, Rebuild, Settings แยกออก + ลบ `admin.py` ทิ้งทั้งไฟล์ | ✅ เสร็จ + ตรวจสอบแล้ว |
| A | AdminWeb: แยก hooks จาก `App.jsx`, แยก component จาก `DocumentsPage.jsx`/`DashboardPage.jsx`, ลบ dead code `handleOpenFaqModal` | ✅ เสร็จ + ตรวจสอบแล้ว |
| U | UserWeb: แยก hooks จาก `App.jsx`, ย้าย pure function ไป `utils/chatUtils.js` | ✅ เสร็จ + ตรวจสอบแล้ว (2026-09-22) — อ่านโค้ดจริงเทียบกับกลไกเปราะบางทั้ง 6 จุดทีละจุดแล้ว ผ่านหมด (ดูรายละเอียดด้านล่าง) |

## วิธีตรวจสอบสถานะจริง (อย่าเชื่อตารางด้านบนเฉยๆ ให้เช็คสดก่อน)

```bash
cd "Z:\Intern\2026\มวล\PJChatbot"
git status --short AdminWeb/ Backend/ UserWeb/
```

- ถ้าเห็น `Backend/app/routers/admin.py` เป็น `D` (deleted) และมีไฟล์ `admin_*.py` ใหม่ๆ ใน
  `Backend/app/routers/` (feedback, unanswered, stats, forms, announcements, history, auth,
  documents, settings, rebuild) → **B1+B2 เสร็จแล้วจริง**
- ถ้าเห็นโฟลเดอร์ `AdminWeb/src/hooks/` มีไฟล์ ~12 ไฟล์ + `AdminWeb/src/pages/LoginPage.jsx` +
  `AdminWeb/src/components/documents/` + `AdminWeb/src/components/dashboard/` → **Phase A
  เสร็จแล้วจริง**
- ถ้าเห็นโฟลเดอร์ `UserWeb/src/hooks/` มีไฟล์ (ดูรายชื่อคาดหวังด้านล่าง) และ
  `UserWeb/src/utils/chatUtils.js` → **Phase U อาจเสร็จแล้ว — ต้องตรวจสอบต่อ (ดูหัวข้อ
  "การตรวจสอบ Phase U" ด้านล่าง) ก่อนถือว่าเสร็จจริง**

Backend มี automated test คุ้มครองอยู่ — รันได้เสมอเพื่อยืนยันว่าไม่มี regression:

```bash
python -m pytest Backend/tests/ web_testing/unit/ web_testing/integration/ -q
```

**ผลลัพธ์ที่ถูกต้อง (baseline ที่ยืนยันแล้วซ้ำแล้วซ้ำเล่าตลอดการรีแฟกเตอร์นี้):**
`177 passed, 2 xfailed, 1 failed` — ตัว failed คือ
`Backend/tests/test_public.py::test_compatibility_search_returns_citations_for_rag_answer`
ซึ่งเป็นบั๊กเดิมที่มีอยู่ก่อนรีแฟกเตอร์ ไม่เกี่ยวกับงานนี้ (บันทึกไว้ใน `web_testing/README.md`)
**ห้ามแก้ตัวนี้แบบ drive-by** — ถ้าเห็นตัวเลขต่างจากนี้ (เช่น fail เพิ่ม, xfail กลายเป็น pass
เพราะ `strict=True`) แปลว่ามี regression จริง ต้องหยุดแล้วตรวจสอบ ไม่ใช่รีบแก้เทสให้ผ่าน

AdminWeb/UserWeb **ไม่มี automated test** (ยกเว้น `UserWeb/vitest.config.js` ที่เพิ่งถูกเพิ่มมา
เร็วๆ นี้ — เช็คว่ามีไฟล์ `.test.js`/`.test.jsx` จริงหรือยังก่อนอาศัยมันเป็นเกณฑ์) —
ต้องตรวจด้วย build/bundle check + code review ด้วยมือแทน (ดูวิธีด้านล่าง)

### ปัญหาสภาพแวดล้อมที่ต้องรู้ไว้ก่อน (ไม่ใช่ regression จากงานนี้)

โปรเจกต์นี้อยู่บน mapped network drive `Z:` ที่ชี้ไปที่ UNC path
`\\192.168.55.14\Share fire\...` (มีช่องว่างในชื่อ share) ทำให้ `vite build` /
`vite dev` ของทั้ง AdminWeb และ UserWeb พังด้วย error ประมาณ:
```
Could not load Z: fire/Intern/2026/.../index.html: ENOENT...
```
**นี่คือบั๊กสภาพแวดล้อมที่มีอยู่ก่อนงานนี้ทั้งหมด ยืนยันแล้วว่าเกิดกับโค้ดต้นฉบับที่ยังไม่แก้ไข
เหมือนกัน (reproduce ได้ด้วยการ `git stash` แล้วรัน `npm run build` ก็ยัง fail แบบเดียวกัน)**
อย่าตีความว่าเป็นความผิดจากการรีแฟกเตอร์ — ให้ใช้ `esbuild` bundle-check แทนตามด้านล่าง

## การตรวจสอบ Phase A (ทำไปแล้ว — ผลลัพธ์ที่ยืนยันแล้ว)

```bash
cd AdminWeb
node_modules/.bin/esbuild src/main.jsx --bundle --loader:.js=jsx --format=esm --jsx=automatic \
  --loader:.woff2=file --loader:.woff=file --loader:.ttf=file --loader:.eot=file \
  --loader:.svg=file --loader:.png=file --loader:.jpg=file --outfile=/tmp/adminweb_check/bundle.js
```
ผลที่ยืนยันแล้ว: bundle สำเร็จ 0 error (มีแค่ output size warning ปกติ)

ไฟล์ที่สร้างใหม่ใน Phase A:
- `AdminWeb/src/hooks/`: useTheme.js, useAuth.js, useProfile.js, useDashboardData.js,
  useSettingsState.js, useDocumentsState.js, useFormsState.js, useAnnouncementsState.js,
  useUsersState.js, useFeedbackAndUnansweredState.js, useHistoryState.js,
  useDeleteConfirmation.js
- `AdminWeb/src/pages/LoginPage.jsx`
- `AdminWeb/src/components/documents/`: ChunkCard.jsx, ChunkEditorGrid.jsx
- `AdminWeb/src/components/dashboard/`: StatCard.jsx, TrendLineChart.jsx,
  CsatDoughnutChart.jsx, PendingQuestionsTable.jsx, ActiveAnnouncementsPanel.jsx,
  TrendDrawer.jsx, AnswerFaqModal.jsx

`App.jsx` เดิม 1786 บรรทัด → เหลือ 591 / `DashboardPage.jsx` 778 → 209 /
`DocumentsPage.jsx` 1146 → 936 — dead code `handleOpenFaqModal` ถูกลบแล้ว (ยืนยันด้วย grep
ว่าไม่มีจุดเรียกใช้เหลืออยู่เลย)

## Phase U — UserWeb (ส่วนที่อาจยังไม่เสร็จ ระวังที่สุด)

**สำคัญมาก**: UserWeb ไม่มีเทสเลย และ UI/พฤติกรรมถูกล็อก (CLAUDE.md ข้อ 3) — ห้ามเปลี่ยน
markup, CSS class, ข้อความไทยที่ผู้ใช้เห็น, หรือ logic การจับคำสำคัญ FAQ ใน `getBotResponse`
เด็ดขาด นี่คืองาน "จัดบ้านใหม่" ล้วนๆ ไม่ใช่แก้ไข feature

### เป้าหมาย
แยก `UserWeb/src/App.jsx` (เดิม 1244 บรรทัด) เป็น custom hooks ใต้ `UserWeb/src/hooks/`
และย้าย pure function ไป `UserWeb/src/utils/chatUtils.js`

### รายชื่อ hook ที่ต้องมี (ตามแผนที่อนุมัติแล้ว)
`useClock.js`, `useTheme.js`, `useSidebarResize.js`, `useFontSize.js`,
`useWelcomeSettings.js`, `useChatSessions.js`, `useFaqVisibility.js`, `useChatInput.js`,
`useSidebarToggle.js`, `useFeedbackModal.js`, `useDislikeModal.js`, `useAnnouncements.js`,
`useUserIp.js` — `showGuide` (boolean เดี่ยว ไม่มี effect) ปล่อยไว้ใน `App.jsx` ได้เลย
ไม่ต้องแยกไฟล์

`getBotResponse`, `escapeHtml`, `parseMarkdown` ย้ายไป `UserWeb/src/utils/chatUtils.js`
เป็น plain export — คอมเมนต์เรื่องความปลอดภัยของ `parseMarkdown` (ป้องกัน `javascript:` URL
scheme) ต้องย้ายตามไปด้วยคำต่อคำ เพราะเป็นคอมเมนต์อธิบายเหตุผลความปลอดภัย ไม่ใช่ของตกแต่ง

### กลไกเปราะบาง 6 จุด — ต้องรักษาให้เหมือนเดิมทุกจุด (นี่คือส่วนที่พังง่ายที่สุด)

1. **`window.__initialActiveSessionId` global side-channel**: ใน initializer ของ
   `useState` สำหรับ `sessions` (ปัจจุบันอยู่ราวบรรทัด 139-235 ของ `App.jsx` เดิม) มีการ
   คำนวณว่าควรสร้าง session ใหม่หรือไม่ (เช็ค inactivity เกิน 1 ชม.) แล้วแอบเซ็ตค่าไว้ที่
   `window.__initialActiveSessionId` จากนั้น initializer ของ `useState` ตัวถัดไป
   (`activeSessionId`, บรรทัด 237-244 เดิม) จะอ่านค่านั้นแล้ว `delete` ทิ้งทันที — ใช้ได้เพราะ
   React รัน initializer ตามลำดับการประกาศ hook เท่านั้น เป็น anti-pattern ที่เปราะมาก
   **มติที่อนุมัติแล้ว**: แทนที่ด้วยฟังก์ชันธรรมดา `computeInitialSessionState()` ที่ return
   `{ sessions, activeSessionId }` ในครั้งเดียว เรียกครั้งเดียวใน `useChatSessions.js` ไม่มี
   global state เลย — ต้องให้ output เหมือนเดิมทุก branch: (ก) ผู้ใช้ใหม่ไม่มี localStorage,
   (ข) มี session ที่ active อยู่แล้วและยังไม่หมดอายุ, (ค) session หมดอายุเกิน 1 ชม. → ต้องสร้าง
   session ใหม่ **และ**ทำให้เป็น active ทันที รวมถึง branch ย่อยเรื่อง backfill
   `session.createdAt` จาก session ID เก่าที่ไม่มีฟิลด์นี้ และ branch "session ล่าสุดมีข้อความ
   เกินกว่าข้อความต้อนรับแล้ว → ต้องสร้าง session ใหม่มาไว้บนสุด"
2. **`handleSendMessage` ใช้ closure ตรงๆ ใน setSessions ครั้งแรก แต่ใช้ functional form ใน
   3 ครั้งหลัง**: การอัปเดตแรก (ทันทีหลังสร้างข้อความผู้ใช้) ใช้ `setSessions(updatedSessions)`
   จาก closure ตรงๆ ส่วน 3 จุดหลัง (ใน `.then()` ตอนสำเร็จ, ใน `.catch()` ตอน AbortError, ใน
   `.catch()` ตอน error ทั่วไป) ใช้ `setSessions(prevSessions => prevSessions.map(...))` —
   **ห้ามทำให้เหมือนกันหมด** เก็บความไม่สมมาตรนี้ไว้ พร้อมคอมเมนต์อธิบายว่าจุดแรกปลอดภัยเพราะ
   รันแบบ sync ก่อนมี await ใดๆ ส่วน 3 จุดหลังรันหลัง async gap จึงต้องใช้ functional form
3. **Effect ของ `showFaqs` ใช้ dependency array แคบมาก**: `useEffect(() => {...},
   [activeSessionId])` เท่านั้น (ทั้งที่ข้างในอ่าน `sessions` ผ่าน `.find`) — ห้ามเพิ่ม
   `sessions` เข้า deps เด็ดขาด เพราะตั้งใจให้ re-evaluate เฉพาะตอนสลับ session ไม่ใช่ทุกครั้งที่
   มีข้อความใหม่ ส่วน `setShowFaqs(false)` ที่เรียกตรงๆ ใน `handleSendMessage` (หลัง
   `setInputValue('')`) ยังต้องอยู่ตรงนั้น เรียก setter ที่ export มาจาก `useFaqVisibility()`
4. **Forced-feedback trigger 2 ใน 3 จุด**: เงื่อนไข `if (nextCount === 3 &&
   sessionStorage.getItem('tuh_feedback_submitted') !== 'true') { setTimeout(...) }` ปรากฏ
   ซ้ำ 2 ที่ (ใน success `.then()` และใน error `.catch()` ทั่วไป) แต่**ไม่มี**ใน AbortError
   branch โดยตั้งใจ (ยกเลิกคำขอไม่ควรนับเป็นการกระตุ้น forced feedback) — ถ้าจะดึงออกมาเป็น
   helper (เช่น `maybeTriggerForcedFeedback(nextCount)`) ต้องเรียกแค่ 2 จุดเดิม พร้อมคอมเมนต์
   อธิบายว่า abort branch ตั้งใจไม่เรียก
5. **Mount effect เดียวทำ 3 fetch พร้อมกัน**: ปัจจุบันมี `useEffect(() => {...}, [])` ตัวเดียว
   ยิง 3 endpoint (`/api/admin/settings`, `/api/announcements/active`, `/api/ip`) —
   ให้แยกเป็น 3 effect แยกกันคนละ hook (`useWelcomeSettings`, `useAnnouncements`,
   `useUserIp`) แต่ละตัวยังคง `[]` deps และไม่มี cleanup (ของเดิมไม่มี cleanup ก็อย่าเพิ่ม)
   — จุดที่ต้องระวัง: settings-fetch effect เรียก `setSessions(prev => ...)` 2 ครั้ง (แพตช์
   welcome message เข้า session-1 กับแพตช์ greeting เข้า session อื่นๆ ที่ยังว่าง) ดังนั้น
   `useWelcomeSettings` ต้องได้ `setSessions` มาจาก `useChatSessions` — เรียก
   `useChatSessions()` ก่อน `useWelcomeSettings()` ใน `App.jsx`
6. **`dislikeMsgId` ต้องเป็น internal state ของ `useDislikeModal.js` เท่านั้น** — ใช้ประกอบ
   payload ตอนส่ง feedback แต่**ห้าม**ส่งเป็น prop ให้ `<DislikeModal>` เด็ดขาด (เช็ค prop list
   ของ component ก่อน/หลังแก้ต้องเหมือนเดิม)

หมายเหตุเพิ่มเติม: `activeSession` และ `isActiveSessionLatest` เป็นค่าที่คำนวณ inline ใน
component body (ไม่ใช่ effect) — และ `handleSendMessage` มีการคำนวณ `isActiveSessionLatest`
ซ้ำอีกรอบที่ต้นฟังก์ชันของตัวเอง (ความซ้ำซ้อนเล็กน้อยที่มีอยู่แล้วในโค้ดเดิม) — **เก็บไว้แบบเดิม
ไม่ต้อง dedupe** เป็นส่วนหนึ่งของงานนี้

### วิธีตรวจสอบ Phase U หลังทำเสร็จ

1. อ่านโค้ดใหม่เทียบกับ 6 ข้อด้านบนทีละข้อ
2. Bundle check ด้วย esbuild (แบบเดียวกับ Phase A):
```bash
cd UserWeb
mkdir -p /tmp/userweb_check
node_modules/.bin/esbuild src/main.jsx --bundle --loader:.js=jsx --format=esm --jsx=automatic \
  --loader:.woff2=file --loader:.woff=file --loader:.ttf=file --loader:.eot=file \
  --loader:.svg=file --loader:.png=file --loader:.jpg=file --outfile=/tmp/userweb_check/bundle.js
```
ต้องได้ 0 error
3. เช็คว่ามี `.test.js`/`.test.jsx` ใน `UserWeb/src/` หรือไม่ (ไฟล์ `vitest.config.js` เพิ่ง
   ถูกเพิ่มมาแยกจากงานนี้) ถ้ามีให้รัน `npx vitest run` ด้วย
4. Manual click-through ตาม checklist ในแผนต้นฉบับ (หัวข้อ "Verification" หมวด UserWeb):
   ทดสอบทักทาย/FAQ โหลดถูกต้อง, ส่ง 3+ ข้อความเพื่อกระตุ้น forced feedback (ต้องขึ้นตอน
   success และตอน error ทั่วไป แต่ต้อง**ไม่**ขึ้นตอนกด stop/cancel), ปรับ
   `localStorage['tuh_last_chat_time']` ให้เก่าเกิน 1 ชม. แล้วโหลดใหม่ (ต้องสร้าง session
   ใหม่และ active ทันที — จุดเสี่ยงสูงสุด), ส่งข้อความรัวๆ, สลับ session (FAQ ต้องโผล่ใหม่)
   vs ส่งข้อความในเซสชันเดิม (FAQ ต้องไม่โผล่), dark mode/sidebar resize/font size คง
   ค่าข้าม reload ได้, like → dislike → ใส่เหตุผล → ส่ง

## กฎโปรเจกต์ที่ต้องรู้ (จาก `CLAUDE.md` ที่ root — อ่านฉบับเต็มด้วย)

- ห้าม push ตรงไปยัง branch `main`
- ห้าม commit ใดๆ เว้นแต่ผู้ใช้ขอให้ commit อย่างชัดเจน (งานทั้งหมดนี้ยังไม่ได้ commit
  โดยตั้งใจ — รอผู้ใช้ตรวจแล้วสั่ง commit เอง)
- ห้ามแก้ RAG pipeline (`Admin/emb.py`, HybridRetriever) — งานรีแฟกเตอร์นี้แค่ย้ายจุดที่
  เรียกใช้ ไม่แตะ pipeline เอง
- ห้ามเปลี่ยนหน้าตา/พฤติกรรม UserWeb โดยไม่ได้รับอนุญาต (ทั้ง Phase U นี้ต้องตรวจสอบตามนี้
  เข้มงวด)
- Database ต้องผ่าน Alembic migration เท่านั้น — งานนี้ไม่ได้แตะ schema เลย ไม่ต้องกังวล
- Backend/AdminWeb/UserWeb ports: 8000 / 5174 / 5173 ตามลำดับ — ห้ามเปลี่ยน

## Phase U เสร็จแล้ว — สรุปผลการตรวจสอบจริง (ไม่ใช่แค่เชื่อ agent report)

`UserWeb/src/App.jsx` เดิม 1244 บรรทัด → เหลือ 439 บรรทัด ไฟล์ใหม่ที่สร้าง:
- `UserWeb/src/utils/chatUtils.js` (88 บรรทัด) — `API_URL`, `DEFAULT_WELCOME_MESSAGE`,
  `DEFAULT_GREETING`, `escapeHtml`, `parseMarkdown` (ใช้ `React.createElement` แทน JSX
  syntax เพราะไฟล์เป็น `.js` ไม่ใช่ `.jsx`), `getBotResponse(text, faqsList)`
- `UserWeb/src/hooks/`: useClock.js, useTheme.js, useSidebarResize.js, useFontSize.js,
  useSidebarToggle.js, useChatSessions.js, useWelcomeSettings.js, useFaqVisibility.js,
  useChatInput.js, useFeedbackModal.js, useDislikeModal.js, useAnnouncements.js,
  useUserIp.js (13 ไฟล์ครบตามแผน)

**ตรวจสอบด้วยตัวเอง (อ่านโค้ดจริงทีละไฟล์ ไม่ได้เชื่อ agent report เฉยๆ) ยืนยันผ่านทั้ง 6
กลไกเปราะบาง**:
1. ✅ `computeInitialSessionState()` ใน `useChatSessions.js` — ตรรกะเหมือนต้นฉบับทุก
   branch ไม่มี `window.__initialActiveSessionId` เหลืออยู่เลย ใช้ `useRef` guard คุมให้
   ฟังก์ชันรันครั้งเดียวต่อ mount (ป้องกัน StrictMode double-invoke ได้ดีกว่าเดิมด้วย)
2. ✅ Asymmetric `setSessions` ใน `useChatInput.js` — จุดแรกยังเป็น closure ตรงๆ, 3 จุดหลัง
   (success/.abort/.error) ยังเป็น functional form พร้อมคอมเมนต์อธิบายเหตุผลไว้ที่จุดเดิม
3. ✅ `useFaqVisibility.js` — `useEffect` ยัง depend แค่ `[activeSessionId]` เท่านั้น
4. ✅ `maybeTriggerForcedFeedback()` ใน `useChatInput.js` — เรียกแค่ 2 จุด (success +
   generic error) ไม่เรียกใน AbortError branch พร้อมคอมเมนต์อธิบาย
5. ✅ แยก mount effect เป็น 3 effect อิสระใน `useWelcomeSettings`/`useAnnouncements`/
   `useUserIp` — `useChatSessions` ถูกเรียกก่อน `useWelcomeSettings` ใน `App.jsx` ตามที่
   ต้องการ (ตรวจแล้วว่า `setSessions` ถูกส่งเข้าไปถูกต้อง)
6. ✅ `dislikeMsgId` ไม่หลุดออกจาก `useDislikeModal.js` เลย — เช็ค prop list ของ
   `<DislikeModal>` ใน `App.jsx` แล้วไม่มี `dislikeMsgId` ปนอยู่ ตรงกับต้นฉบับ 100%

**Bundle check ด้วย esbuild ยืนยันแล้ว (ตัวเอง รันซ้ำเอง ไม่ใช่แค่ agent บอก)**:
```bash
cd UserWeb
node_modules/.bin/esbuild src/main.jsx --bundle --loader:.js=jsx --format=esm --jsx=automatic \
  --loader:.woff2=file --loader:.woff=file --loader:.ttf=file --loader:.eot=file \
  --loader:.svg=file --loader:.png=file --loader:.jpg=file --outfile=/tmp/userweb_check/bundle.js
```
ผลลัพธ์: **สำเร็จ 0 error**

**สิ่งที่ยังไม่ได้ทำ (เพราะ sandbox รัน dev server ไม่ได้ — บั๊ก network drive เดิม)**:
Manual click-through ตาม checklist ในแผนต้นฉบับยังไม่ได้ทำจริงในเบราว์เซอร์ — แนะนำให้ผู้ใช้
รัน `npm run dev -- --port 5173` (บนเครื่องที่ไม่มีปัญหา mapped-drive) แล้วเช็คตาม 8 ข้อใน
checklist ของแผน (ทักทาย/FAQ, forced feedback หลัง 3 ข้อความ ต้องไม่ขึ้นตอนกด stop, จำลอง
session หมดอายุเกิน 1 ชม., ส่งข้อความรัว, สลับ session vs ส่งในเซสชันเดิม, dark
mode/sidebar/font ข้าม reload, like→dislike→submit) ก่อน commit เพื่อความมั่นใจสูงสุด
เนื่องจากนี่คือโค้ดที่ไม่มี automated test คุ้มครองอยู่เลย

## สรุปงานรีแฟกเตอร์ทั้งหมด (เสร็จสมบูรณ์ตามแผนแล้ว)

- **Backend**: `admin.py` (1549 บรรทัด) → ลบทิ้งทั้งไฟล์ แยกเป็น 10 router +
  6 service ไฟล์ — ผ่านเทสครบ `177 passed, 2 xfailed, 1 failed (pre-existing)` ทุกครั้ง
- **AdminWeb**: `App.jsx` (1786→591), `DashboardPage.jsx` (778→209),
  `DocumentsPage.jsx` (1146→936) — ผ่าน esbuild bundle check, dead code ลบแล้ว
- **UserWeb**: `App.jsx` (1244→439) — ผ่าน esbuild bundle check + ตรวจกลไกเปราะบาง 6/6
  ผ่าน — **เหลือแค่ manual click-through ในเบราว์เซอร์จริงก่อน commit**

**ห้าม commit ใดๆ เองโดยไม่มีผู้ใช้สั่ง** — งานทั้งหมดนี้ยังไม่ได้ commit โดยตั้งใจ รอผู้ใช้ตรวจ
แล้วสั่ง commit/สร้าง PR เอง
