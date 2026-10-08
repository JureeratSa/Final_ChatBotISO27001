/**
 * LoginPage — หน้าจอเข้าสู่ระบบแอดมิน แสดงก่อน login สำเร็จ จึงรับค่าทุกอย่างผ่าน props
 * โดยตรงจาก App.jsx (ไม่ผ่าน AdminContext เพราะ context นั้น gate อยู่หลัง login แล้วเท่านั้น)
 * แยกออกมาจาก App.jsx เดิม
 */
export default function LoginPage({
  successMsg,
  errorMsg,
  loginError,
  loginLoading,
  username,
  setUsername,
  password,
  setPassword,
  showPassword,
  setShowPassword,
  handleLogin,
}) {
  return (
    <div className="min-h-screen bg-tuh-navy text-white flex flex-col justify-center items-center relative overflow-hidden px-4">
      {successMsg && (
        <div className="fixed top-5 right-5 z-50 p-4 bg-emerald-500 text-white rounded-2xl shadow-xl flex items-center gap-2.5 font-bold animate-slide-in">
          <i className="fa-solid fa-circle-check text-lg"></i>
          {successMsg}
        </div>
      )}
      {errorMsg && (
        <div className="fixed top-5 right-5 z-50 p-4 bg-red-500 text-white rounded-2xl shadow-xl flex items-center gap-2.5 font-bold animate-slide-in">
          <i className="fa-solid fa-circle-exclamation text-lg"></i>
          {errorMsg}
        </div>
      )}
      {/* Floating Light Elements */}
      <div className="absolute top-20 right-20 w-80 h-80 rounded-full bg-tuh-purple/20 blur-[120px] pointer-events-none animate-float-slow"></div>
      <div className="absolute bottom-20 left-20 w-80 h-80 rounded-full bg-tuh-rose/10 blur-[120px] pointer-events-none animate-float-slower"></div>

      <div className="w-full max-w-md bg-white/10 dark:bg-[#2c0548]/25 backdrop-blur-xl p-8 rounded-3xl border border-white/10 shadow-2xl relative z-10 animate-slide-in">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-tuh-gradient-2 mx-auto rounded-2xl flex items-center justify-center text-white text-3xl shadow-lg mb-4 animate-bounce">
            <i className="fa-solid fa-screwdriver-wrench"></i>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">TUH Chatbot Admin</h1>
          <p className="text-sm text-slate-300 mt-1">ระบบตั้งค่าและวิเคราะห์ข้อมูล สำหรับผู้ดูแลระบบ</p>
        </div>

        {loginError && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-2xl text-red-200 text-sm flex items-center gap-2 font-medium">
            <i className="fa-solid fa-circle-exclamation text-base"></i>
            {loginError}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">Username</label>
            <div className="relative">
              <i className="fa-solid fa-user absolute left-4 top-3.5 text-slate-500 dark:text-slate-400"></i>
              <input
                type="text"
                required
                placeholder="ชื่อผู้ใช้งานแอดมิน"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-11 pr-4 text-white placeholder-slate-500 focus:outline-none focus:border-tuh-rose transition font-semibold"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">Password</label>
            <div className="relative">
              <i className="fa-solid fa-lock absolute left-4 top-3.5 text-slate-500 dark:text-slate-400"></i>
              <input
                type={showPassword ? "text" : "password"}
                required
                placeholder="รหัสผ่านเข้าใช้งาน"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-11 pr-12 text-white placeholder-slate-500 focus:outline-none focus:border-tuh-rose transition font-semibold"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-3.5 text-orange-500 hover:text-orange-400 transition-colors focus:outline-none cursor-pointer"
              >
                <i className={`fa-solid ${showPassword ? 'fa-eye' : 'fa-eye-slash'}`}></i>
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loginLoading}
            className="w-full bg-tuh-gradient-2 text-white font-bold py-3.5 rounded-2xl hover:shadow-lg hover:shadow-tuh-rose/30 hover:scale-[1.02] transition active:scale-[0.98] flex justify-center items-center gap-2"
          >
            {loginLoading ? (
              <>
                <i className="fa-solid fa-circle-notch animate-spin"></i>
                กำลังตรวจสอบสิทธิ์...
              </>
            ) : (
              <>
                <i className="fa-solid fa-right-to-bracket"></i>
                เข้าสู่ระบบแอดมิน
              </>
            )}
          </button>
        </form>

        <div className="mt-8 text-center text-xs text-slate-500 dark:text-slate-400 font-semibold">
          งานสารสนเทศ โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ
        </div>
      </div>
    </div>
  );
}
