import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store/index.tsx';
import entries from 'lodash/entries';
import filter from 'lodash/filter';
import { useShallow } from 'zustand/react/shallow';

export const useRunItem = useGroupedRunStore(
    useShallow((state) => ({
        runItem: Object.fromEntries(filter(entries(state.runItem), ([key]) => key !== 'complete_time'))
    })),
)
