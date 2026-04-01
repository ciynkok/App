import { create } from 'zustand';

export const useBoardStore = create((set, get) => ({
  board: null,
  columns: [],
  tasks: [],
  onlineUsers: [],
  comments: {},
  setBoard: (board) => set({ board }),
  setColumns: (columns) => set({ columns }),
  setTasks: (tasks) => set({ tasks }),
  addTask: (task) => set((state) => ({ tasks: [...state.tasks, task] })),
  updateTask: (taskId, updates) => set((state) => ({
    tasks: state.tasks.map(t => t.id === taskId ? { ...t, ...updates } : t)
  })),
  removeTask: (taskId) => set((state) => ({
    tasks: state.tasks.filter(t => t.id !== taskId)
  })),
  setOnlineUsers: (users) => set({ onlineUsers: users }),
  addOnlineUser: (user) => set((state) => ({
    onlineUsers: [...state.onlineUsers.filter(u => u.id !== user.id), user]
  })),
  removeOnlineUser: (userId) => set((state) => ({
    onlineUsers: state.onlineUsers.filter(u => u.id !== userId)
  })),
  setComments: (taskId, comments) => set((state) => ({
    comments: { ...state.comments, [taskId]: comments }
  })),
  addComment: (taskId, comment) => set((state) => ({
    comments: {
      ...state.comments,
      [taskId]: [...(state.comments[taskId] || []), comment]
    }
  })),
  removeComment: (taskId, commentId) => set((state) => ({
    comments: {
      ...state.comments,
      [taskId]: (state.comments[taskId] || []).filter(c => c.id !== commentId)
    }
  })),
}));
