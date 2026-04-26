import { create } from 'zustand';

const useSettings = create((set) => ({
  dailyCap: 20,
  setDailyCap: (cap) => set({ dailyCap: cap }),
}));

export default useSettings;
