import { createContext } from 'react';
import type { CalculoContextValue } from './CalculoContext';

export const CalculoContext = createContext<CalculoContextValue | null>(null);
