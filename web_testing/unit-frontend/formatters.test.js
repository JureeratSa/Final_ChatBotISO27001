// Unit Test — UserWeb Frontend Formatters (FE-01, FE-02)
// อ้างอิง: แผนทดสอบเว็บ T3 (ชั้น Unit Test) — เรียก UserWeb/src/utils/formatters.js ตรงๆ
// หมายเหตุ: FE-01/FE-02 เป็นรหัสเสริมนอกเหนือจาก UT-01 ถึง UT-14 ในเอกสาร "แผนทดสอบเว็บ" เดิม
// (เอกสารเดิมไม่ได้ระบุ test case ฝั่ง frontend ไว้) ยังไม่ได้เพิ่มเข้าเอกสารแผนทดสอบอย่างเป็นทางการ
//
// stripHtml/formatAnnDate แยกออกมาจาก UserWeb/src/App.jsx เพื่อ unit test ได้โดยไม่ต้อง render
// component เต็มรูปแบบ — logic และพฤติกรรมเดิมทุกกรณี ไม่ได้แก้ไข (ดู UserWeb/src/utils/formatters.js)
import { describe, it, expect } from 'vitest';
import { stripHtml, formatAnnDate } from '../../UserWeb/src/utils/formatters.js';

// ─── FE-01: stripHtml — ตัด HTML tag ออกเหลือแค่ข้อความล้วนสำหรับแสดงในการ์ดประกาศ ──

describe('stripHtml (FE-01)', () => {
  it('คืนค่าว่างเมื่อ input เป็น null', () => {
    expect(stripHtml(null)).toBe('');
  });

  it('คืนค่าว่างเมื่อ input เป็น empty string', () => {
    expect(stripHtml('')).toBe('');
  });

  it('ตัด tag ธรรมดาออกเหลือแค่ข้อความ', () => {
    expect(stripHtml('<p>Hello <b>World</b></p>')).toBe('Hello World');
  });

  it('ถอดรหัส HTML entity กลับเป็นตัวอักษรจริง', () => {
    expect(stripHtml('A &amp; B &lt;3')).toBe('A & B <3');
  });

  it('EG — เนื้อหาภายใน <script> ไม่รวมอยู่ใน textContent (ตรวจแล้วด้วยการรันจริงใน jsdom ไม่ได้เดา)', () => {
    // ผลจริงจากการรัน: 'Hi' เท่านั้น ไม่มี 'alert(1)' ปนมา — DOMParser (jsdom) ไม่นับเนื้อหาใน
    // <script> เป็นส่วนหนึ่งของ textContent ถึงกระนั้น ฟังก์ชันนี้มีไว้แสดงผล preview เฉยๆ
    // ความปลอดภัยจริงมาจาก sanitize_html() ฝั่ง Backend (nh3, ดู UT-06/UT-07) ก่อนข้อมูลจะถูก
    // เก็บลง DB ตั้งแต่ต้นทางแล้ว ไม่ได้พึ่ง stripHtml() ฝั่ง frontend เป็นด่านความปลอดภัย
    expect(stripHtml('<script>alert(1)</script>Hi')).toBe('Hi');
  });
});

// ─── FE-02: formatAnnDate — แปลงวันที่ ISO เป็นรูปแบบไทย (วัน เดือนย่อ พ.ศ.) ──────

describe('formatAnnDate (FE-02)', () => {
  it('คืนค่าว่างเมื่อ input เป็น null', () => {
    expect(formatAnnDate(null)).toBe('');
  });

  it('คืนค่าว่างเมื่อ input เป็น undefined', () => {
    expect(formatAnnDate(undefined)).toBe('');
  });

  it('แปลงวันที่ล้วน (ไม่มีเวลา) เป็นรูปแบบไทยถูกต้อง', () => {
    expect(formatAnnDate('2026-09-21')).toBe('21 ก.ย. 2569');
  });

  it('แปลงวันที่+เวลา (ISO พร้อม T) เป็นรูปแบบไทยพร้อมเวลาถูกต้อง', () => {
    expect(formatAnnDate('2026-09-21T14:30:00')).toBe('21 ก.ย. 2569 เวลา 14:30 น.');
  });

  it('EG — string ที่ไม่มี "-" เลย (parts[0].split("-") ได้ length 1) คืนค่าเดิมโดยไม่แปลง', () => {
    expect(formatAnnDate('invalid')).toBe('invalid');
  });

  it('BVA — เดือนแรกและเดือนสุดท้ายของปี แปลงชื่อเดือนย่อไทยถูกต้อง', () => {
    expect(formatAnnDate('2026-01-01')).toBe('1 ม.ค. 2569');
    expect(formatAnnDate('2026-12-31')).toBe('31 ธ.ค. 2569');
  });

  it('EG — ค่าที่ไม่ใช่ตัวเลขแต่แยกด้วย "-" ได้ 3 ส่วนพอดี (เช่น "abcd-ef-gh") จะไม่ถูกดักด้วย length check และคืนค่าที่มี NaN/undefined ปน — พฤติกรรมเดิมของโค้ด ยังไม่ได้แก้เพราะเป็นการเปลี่ยน behavior ของ UserWeb ที่ต้องขออนุญาตแยกต่างหาก (CLAUDE.md กฎข้อ 3)', () => {
    expect(formatAnnDate('abcd-ef-gh')).toBe('NaN undefined NaN');
  });
});
