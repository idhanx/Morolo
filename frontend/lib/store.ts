/**
 * Zustand global store.
 */

import { create } from "zustand";

interface MoroloStore {
    currentDocId: string | null;
    setCurrentDocId: (docId: string | null) => void;
}

export const useMoroloStore = create<MoroloStore>((set) => ({
    currentDocId: null,
    setCurrentDocId: (docId) => set({ currentDocId: docId }),
}));
