/**
 * 用户状态管理
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UserInfo {
  id: number;
  username: string;
  email?: string;
  full_name?: string;
  role: string;
  department?: string;
}

interface UserState {
  userInfo: UserInfo | null;
  token: string | null;
  isAuthenticated: boolean;
  setUserInfo: (user: UserInfo) => void;
  setToken: (token: string) => void;
  logout: () => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      userInfo: null,
      token: null,
      isAuthenticated: false,

      setUserInfo: (user) => set({ userInfo: user }),
      setToken: (token) => {
        localStorage.setItem('token', token);
        set({ token, isAuthenticated: true });
      },
      logout: () => {
        localStorage.removeItem('token');
        set({ userInfo: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: 'user-storage',
    }
  )
);
