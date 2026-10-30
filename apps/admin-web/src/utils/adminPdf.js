/**
 * เปิด/ดาวน์โหลด PDF ของเอกสารผ่าน /api/admin/documents/file (ต้องแนบ token)
 * เดิมใช้ <a href="/api/documents/serve|download/..."> ตรงๆ ซึ่งเปิดให้คนทั่วไปโหลดได้ทุกไฟล์ —
 * ตอนนี้ endpoint สาธารณะส่งเฉพาะเอกสาร Active ฝั่งแอดมิน (รวมฉบับร่าง) จึงต้องโหลดด้วย token แล้วเปิดเป็น blob
 */
export async function openAdminPdf(apiUrl, filename, { page, download = false } = {}) {
  // เปิดแท็บไว้ก่อนตั้งแต่ตอนคลิก — ถ้าเปิดหลัง await เบราว์เซอร์จะมองเป็น popup แล้วบล็อก
  const tab = download ? null : window.open('', '_blank');
  try {
    const params = new URLSearchParams({ filename, download: download ? 'true' : 'false' });
    const res = await fetch(`${apiUrl}/api/admin/documents/file?${params}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('tuh_admin_token') || ''}` },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'เปิดไฟล์ไม่สำเร็จ');
    }
    const url = URL.createObjectURL(await res.blob());
    if (download) {
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
    } else {
      tab.location.href = page ? `${url}#page=${page}` : url;
    }
    // ปล่อยหน่วยความจำทีหลัง — แท็บที่เปิดอยู่ยังต้องอ่าน blob นี้สักพัก
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (err) {
    if (tab) tab.close();
    window.alert(err.message);
  }
}
