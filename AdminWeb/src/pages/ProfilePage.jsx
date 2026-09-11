import { useAdminContext } from '../context/AdminContext';
import botAvatar from '../bot_avatar.jpg';

/**
 * ProfilePage — แท็บ "โปรไฟล์แอดมิน" แสดงข้อมูลบัญชีปัจจุบันและฟอร์มเปลี่ยนรหัสผ่าน
 * แยกออกมาจาก App.jsx เดิม
 */
export default function ProfilePage() {
  const {
    adminUser,
    confirmPassword,
    handleUpdatePassword,
    newPassword,
    setConfirmPassword,
    setNewPassword,
    setShowConfirmPassword,
    setShowNewPassword,
    showConfirmPassword,
    showNewPassword,
  } = useAdminContext();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-in">

      {/* Profile Card */}
      <div className="p-6 tuh-glass-1 rounded-3xl shadow-sm text-center space-y-4">
        <div className="w-24 h-24 rounded-full mx-auto shadow-md overflow-hidden border-4 border-white dark:border-tuh-purple/30 bg-slate-100 flex items-center justify-center">
          <img src={botAvatar} alt="Admin Profile" className="w-full h-full object-cover" />
        </div>
        <div>
          <h3 className="text-xl font-black">{adminUser.name}</h3>
          <p className="text-xs text-tuh-rose font-black uppercase mt-1 tracking-wider">{adminUser.role}</p>
        </div>
        <div className="border-t border-slate-100 dark:border-tuh-purple/20 pt-4 text-sm text-slate-500 dark:text-slate-400 font-bold space-y-2">
          <div className="flex justify-between">
            <span>Username:</span>
            <span className="text-slate-800 dark:text-white">admin</span>
          </div>
        </div>
      </div>

      {/* Password change form */}
      <div className="lg:col-span-2 p-6 tuh-glass-1 rounded-3xl shadow-sm space-y-6">
        <h3 className="text-lg font-extrabold flex items-center gap-2 border-b border-slate-100 dark:border-tuh-purple/20 pb-4">
          <i className="fa-solid fa-shield-halved text-tuh-rose"></i>
          เปลี่ยนรหัสผ่านแอดมิน (Admin Security)
        </h3>

        <form onSubmit={handleUpdatePassword} className="space-y-4 max-w-md">
          <div>
            <label className="block text-sm font-bold mb-2">รหัสผ่านแอดมินใหม่</label>
            <div className="relative">
              <input
                type={showNewPassword ? "text" : "password"}
                placeholder="ตั้งรหัสผ่านใหม่"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full tuh-glass-2 rounded-2xl py-3 pl-4 pr-12 focus:outline-none focus:border-tuh-rose transition font-semibold"
              />
              <button
                type="button"
                onClick={() => setShowNewPassword(!showNewPassword)}
                className="absolute right-4 top-3.5 text-orange-500 hover:text-orange-600 dark:text-orange-400 dark:hover:text-orange-350 transition-colors focus:outline-none cursor-pointer"
              >
                <i className={`fa-solid ${showNewPassword ? 'fa-eye' : 'fa-eye-slash'}`}></i>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold mb-2">ยืนยันรหัสผ่านแอดมินใหม่อีกครั้ง</label>
            <div className="relative">
              <input
                type={showConfirmPassword ? "text" : "password"}
                placeholder="พิมพ์ยืนยันรหัสผ่านใหม่"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full tuh-glass-2 rounded-2xl py-3 pl-4 pr-12 focus:outline-none focus:border-tuh-rose transition font-semibold"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-4 top-3.5 text-orange-500 hover:text-orange-600 dark:text-orange-400 dark:hover:text-orange-350 transition-colors focus:outline-none cursor-pointer"
              >
                <i className={`fa-solid ${showConfirmPassword ? 'fa-eye' : 'fa-eye-slash'}`}></i>
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="inline-flex items-center gap-1.5 bg-tuh-rose hover:bg-tuh-rose/90 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98]"
          >
            <i className="fa-solid fa-lock-open"></i> เปลี่ยนรหัสผ่านความปลอดภัย
          </button>
        </form>
      </div>

    </div>
  );
}
