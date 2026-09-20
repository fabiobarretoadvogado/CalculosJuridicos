import { useContext } from 'react';
import type { CalculoContextValue } from './CalculoContext';
import { CalculoContext } from './CalculoContextBase';

export function useCalculo(): CalculoContextValue {
  const context = useContext(CalculoContext);
  if (!context) {
    throw new Error('useCalculo deve ser usado dentro de <CalculoProvider>');
  }
  return context;
}
