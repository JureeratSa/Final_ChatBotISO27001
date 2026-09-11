import { useAdminContext } from '../context/AdminContext';

/**
 * UsersPage — แท็บ "จัดการบัญชีแอดมิน" (เฉพาะ System Administrator) ตารางรายชื่อแอดมิน
 * พร้อม modal เพิ่ม/แก้ไข/รีเซ็ตรหัสผ่าน — แยกออกมาจาก App.jsx เดิม
 */
export default function UsersPage() {
  const {
    adminUser,
    handleCreateOrUpdateUser,
    loadingUsers,
    selectedUser,
    setDeleteModalState,
    setSelectedUser,
    setShowUserModal,
    setUserFormDepartment,
    setUserFormDisplayName,
    setUserFormIsActive,
    setUserFormMode,
    setUserFormPassword,
    setUserFormRole,
    setUserFormUsername,
    showUserModal,
    userFormDepartment,
    userFormDisplayName,
    userFormIsActive,
    userFormMode,
    userFormPassword,
    userFormRole,
    userFormUsername,
    users,
  } = useAdminContext();

  return (
    <>
      <div className="space-y-6 animate-slide-in">
        <div className="tuh-glass-1 rounded-3xl overflow-hidden shadow-sm">
          <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-extrabold flex items-center gap-2">
                <i className="fa-solid fa-users-gear text-tuh-rose"></i> การบริหารจัดการสิทธิ์บัญชีผู้ดูแลระบบ (Administrators)
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">
                คุณสามารถสร้าง แก้ไข หรือลบบัญชีแอดมิน รวมถึงรีเซ็ตรหัสผ่านและเปลี่ยนสิทธิ์การเข้าถึงระบบได้ที่นี่
              </p>
            </div>
            <button
              onClick={() => {
                setUserFormMode('create');
                setSelectedUser(null);
                setUserFormUsername('');
                setUserFormPassword('');
                setUserFormDisplayName('');
                setUserFormRole('admin');
                setUserFormIsActive(true);
                setUserFormDepartment('');
                setShowUserModal(true);
              }}
              className="bg-tuh-rose hover:bg-tuh-rose/90 text-white font-bold py-2.5 px-4 rounded-xl active:scale-[0.98] transition flex items-center gap-2 text-xs shadow-sm"
            >
              <i className="fa-solid fa-user-plus"></i> เพิ่มแอดมินใหม่
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[800px]">
              <thead>
                <tr className="bg-slate-100 dark:bg-tuh-navy/30 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20">
                  <th className="px-6 py-4">ชื่อแสดงผล (Display Name)</th>
                  <th className="px-6 py-4">Username</th>
                  <th className="px-6 py-4">หมวดงาน (Department)</th>
                  <th className="px-6 py-4">บทบาท (Role)</th>
                  <th className="px-6 py-4 text-center">สถานะใช้งาน</th>
                  <th className="px-6 py-4 text-center">วันที่สร้างบัญชี</th>
                  <th className="px-6 py-4 text-right">การจัดการ</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-sm font-semibold">
                {loadingUsers ? (
                  <tr>
                    <td colSpan="6" className="px-6 py-12 text-center text-slate-500 font-bold">
                      <div className="inline-block w-6 h-6 border-2 border-tuh-rose border-t-transparent rounded-full animate-spin mr-2"></div>
                      กำลังโหลดรายชื่อแอดมิน...
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="px-6 py-12 text-center text-slate-500 dark:text-slate-400 font-bold">
                      ไม่พบบัญชีผู้ใช้ใดๆ ในระบบ
                    </td>
                  </tr>
                ) : (
                  users.map((u) => {
                    const isSelf = adminUser.username === u.username;
                    return (
                      <tr key={u.id} className="hover:bg-slate-50/50 dark:hover:bg-tuh-indigo/10 transition">
                        <td className="px-6 py-4 text-slate-800 dark:text-slate-100 font-bold">
                          {u.display_name} {isSelf && <span className="text-[10px] bg-sky-500/10 text-sky-500 px-1.5 py-0.5 rounded font-extrabold ml-1">บัญชีของคุณ</span>}
                        </td>
                        <td className="px-6 py-4 text-slate-600 dark:text-slate-305">
                          {u.username}
                        </td>
                        <td className="px-6 py-4 text-slate-600 dark:text-slate-305 font-bold">
                          {u.department || 'ทั่วไป'}
                        </td>
                        <td className="px-6 py-4 align-top">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-extrabold ${u.role === 'System Administrator'
                            ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400'
                            : 'bg-slate-500/10 text-slate-600 dark:text-slate-400'
                            }`}>
                            {u.role}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-xs font-extrabold ${u.is_active
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                            : 'bg-rose-500/10 text-rose-600 dark:text-rose-400'
                            }`}>
                            {u.is_active ? "พร้อมใช้งาน" : "ระงับชั่วคราว"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center text-xs text-slate-500 dark:text-slate-400">
                          {new Date(u.created_at).toLocaleString('th-TH', { dateStyle: 'medium', timeStyle: 'short' })}
                        </td>
                        <td className="px-6 py-4 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => {
                                setUserFormMode('edit');
                                setSelectedUser(u);
                                setUserFormUsername(u.username);
                                setUserFormPassword('');
                                setUserFormDisplayName(u.display_name);
                                setUserFormRole(u.role);
                                setUserFormIsActive(u.is_active);
                                setUserFormDepartment(u.department || '');
                                setShowUserModal(true);
                              }}
                              className="bg-amber-500 hover:bg-amber-600 text-white font-bold py-1.5 px-3 rounded-xl transition active:scale-95 text-xs flex items-center gap-1"
                            >
                              <i className="fa-solid fa-pen-to-square"></i> แก้ไข / รีเซ็ตรหัส
                            </button>
                            <button
                              onClick={() => setDeleteModalState({ show: true, type: 'user', targetId: u.id, targetName: u.username })}
                              disabled={isSelf}
                              className="bg-rose-500 hover:bg-rose-600 disabled:opacity-30 disabled:cursor-not-allowed text-white font-bold py-1.5 px-3 rounded-xl transition active:scale-95 text-xs flex items-center gap-1"
                            >
                              <i className="fa-solid fa-trash"></i> ลบ
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* MODAL: ADD / EDIT ADMIN USER MODAL */}
      {showUserModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md tuh-glass-1 tuh-border-glass-strong rounded-3xl shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-user-gear text-tuh-rose"></i>
                {userFormMode === 'create' ? 'เพิ่มผู้ดูแลระบบ (Admin) ใหม่' : 'แก้ไขข้อมูลบัญชีแอดมิน'}
              </h3>
              <button
                onClick={() => { setShowUserModal(false); setSelectedUser(null); }}
                className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <form onSubmit={handleCreateOrUpdateUser} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">ชื่อแสดงผล (Display Name)</label>
                <input
                  type="text"
                  required
                  placeholder="เช่น สมชาย ใจดี"
                  value={userFormDisplayName}
                  onChange={(e) => setUserFormDisplayName(e.target.value)}
                  className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Username (ใช้เข้าระบบ)</label>
                <input
                  type="text"
                  required
                  disabled={userFormMode === 'edit'}
                  placeholder="เช่น somchayd"
                  value={userFormUsername}
                  onChange={(e) => setUserFormUsername(e.target.value)}
                  className="w-full tuh-glass-2 disabled:opacity-50 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">หมวดงาน / แผนก (Department)</label>
                <input
                  type="text"
                  placeholder="เช่น ไอที, ประชาสัมพันธ์, การเงิน"
                  value={userFormDepartment}
                  onChange={(e) => setUserFormDepartment(e.target.value)}
                  className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                  {userFormMode === 'create' ? 'รหัสผ่าน (Password)' : 'ตั้งรหัสผ่านใหม่ (Reset Password)'}
                  {userFormMode === 'edit' && <span className="text-[10px] text-slate-400 font-normal ml-1">(ปล่อยว่างไว้หากต้องการรักษารหัสผ่านเดิม)</span>}
                </label>
                <input
                  type="password"
                  required={userFormMode === 'create'}
                  placeholder={userFormMode === 'create' ? "พิมพ์รหัสผ่านสำหรับล็อกอิน..." : "ปล่อยว่างเพื่อไม่เปลี่ยน หรือพิมพ์รหัสใหม่..."}
                  value={userFormPassword}
                  onChange={(e) => setUserFormPassword(e.target.value)}
                  className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">บทบาท (Role)</label>
                  <select
                    value={userFormRole}
                    onChange={(e) => setUserFormRole(e.target.value)}
                    className="w-full tuh-glass-2 rounded-2xl py-2.5 px-3 focus:outline-none focus:border-tuh-rose transition font-bold text-xs text-tuh-navy dark:text-white"
                  >
                    <option value="admin">admin</option>
                    <option value="System Administrator">System Administrator</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">สถานะใช้งาน</label>
                  <div className="flex items-center h-10 mt-1">
                    <label className="relative inline-flex items-center cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={userFormIsActive}
                        onChange={(e) => setUserFormIsActive(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-white/10 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-none peer-checked:bg-emerald-500 dark:peer-checked:bg-emerald-500"></div>
                      <span className="ml-2 text-xs font-bold text-slate-600 dark:text-slate-300">
                        {userFormIsActive ? "เปิดการใช้งาน" : "ระงับสิทธิ์"}
                      </span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100 dark:border-tuh-purple/10">
                <button
                  type="button"
                  onClick={() => { setShowUserModal(false); setSelectedUser(null); }}
                  className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95 text-xs"
                >
                  ยกเลิก
                </button>
                <button
                  type="submit"
                  className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98] text-xs flex items-center gap-1.5"
                >
                  <i className="fa-solid fa-floppy-disk"></i> บันทึกข้อมูล
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
