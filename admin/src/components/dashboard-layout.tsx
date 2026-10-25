"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "./sidebar";
import { getSavedToken } from "@/lib/api";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const pathname = usePathname();
  const router = useRouter();

  const isLoginPage = pathname === "/login";

  useEffect(() => {
    if (isLoginPage) {
      setIsAuthenticated(true);
      return;
    }

    const token = getSavedToken();
    if (!token) {
      setIsAuthenticated(false);
      router.replace("/login");
    } else {
      setIsAuthenticated(true);
    }
  }, [pathname, isLoginPage, router]);

  // If this is the login page, render children directly without dashboard chrome
  if (isLoginPage) {
    return <>{children}</>;
  }

  // Initial loading state while verifying local auth
  if (isAuthenticated === null || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium text-slate-400">Avtorizatsiya tekshirilmoqda...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-slate-900/50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar Wrapper */}
      <div 
        className={`fixed inset-y-0 left-0 z-50 transform md:relative md:translate-x-0 transition duration-200 ease-in-out ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      <div className="flex-1 flex flex-col overflow-hidden w-full">
        {/* Mobile Header */}
        <header className="md:hidden flex items-center justify-between bg-white border-b border-slate-200 px-4 h-16 shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-sm font-bold">⚖️</span>
            </div>
            <span className="text-lg font-bold text-slate-900">Yurist Admin</span>
          </div>
          <button 
            onClick={() => setSidebarOpen(true)}
            className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto w-full">
          <div className="p-4 md:p-6 lg:p-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
