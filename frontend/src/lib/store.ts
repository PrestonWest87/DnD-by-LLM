import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from './api'

interface User {
  id: number
  username: string
  email: string
  is_admin?: boolean
}

interface Profile {
  id: number
  display_name: string
  avatar_url: string
  theme: string
  preferences: Record<string, any>
}

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
  profile: Profile | null
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => void
  setUser: (user: User) => void
  fetchProfile: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,
      profile: null,

      login: async (username: string, password: string) => {
        const formData = new FormData()
        formData.append('username', username)
        formData.append('password', password)
        const response = await api.post('/auth/login', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        set({ token: response.data.access_token, refreshToken: response.data.refresh_token })
        const userResponse = await api.get('/auth/me')
        set({ user: userResponse.data })
        await get().fetchProfile()
      },

      register: async (username: string, email: string, password: string) => {
        try {
          await api.post('/auth/register', { username, email, password })
        } catch (err: any) {
          if (err.response?.status === 400) {
            throw new Error(err.response.data?.detail || 'Registration failed')
          }
          throw err
        }
        const formData = new FormData()
        formData.append('username', username)
        formData.append('password', password)
        const response = await api.post('/auth/login', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        set({ token: response.data.access_token, refreshToken: response.data.refresh_token })
        const userResponse = await api.get('/auth/me')
        set({ user: userResponse.data })
        await get().fetchProfile()
      },

      logout: () => {
        set({ token: null, refreshToken: null, user: null, profile: null })
      },

      setUser: (user: User) => {
        set({ user })
      },

      fetchProfile: async () => {
        try {
          const response = await api.get('/profile')
          set({ profile: response.data })
        } catch (err) {
          console.error('Failed to fetch profile:', err)
        }
      },
    }),
    {
      name: 'dragonforge-auth',
      partialize: (state) => ({ token: state.token, refreshToken: state.refreshToken }),
    }
  )
)

interface GameState {
  currentCampaign: any | null
  currentRoom: any | null
  currentCharacter: any | null
  messages: any[]
  setCurrentCampaign: (campaign: any) => void
  setCurrentRoom: (room: any) => void
  setCurrentCharacter: (character: any) => void
  addMessage: (message: any) => void
  clearMessages: () => void
}

export const useGameStore = create<GameState>((set) => ({
  currentCampaign: null,
  currentRoom: null,
  currentCharacter: null,
  messages: [],

  setCurrentCampaign: (campaign) => set({ currentCampaign: campaign }),
  setCurrentRoom: (room) => set({ currentRoom: room }),
  setCurrentCharacter: (character) => set({ currentCharacter: character }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  clearMessages: () => set({ messages: [] }),
}))