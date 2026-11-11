import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react';
import { destinoDaInsercao, reordenarParcelas } from './reordenarParcelas';

interface Arraste {
  numero: number;
  pointerId: number;
  inicioY: number;
  x: number;
  y: number;
  ativo: boolean;
  insercao: number | null;
  botao: HTMLButtonElement;
}

export function useReordenacaoParcelas<T extends { numero: number }>(
  parcelas: T[], onChange: (parcelas: T[]) => void, desabilitado: boolean,
) {
  const listaRef = useRef<HTMLElement | null>(null);
  const arrasteRef = useRef<Arraste | null>(null);
  const animacaoRef = useRef<number | null>(null);
  const focoDestinoRef = useRef<number | null>(null);
  const [arrastada, setArrastada] = useState<number | null>(null);
  const [insercao, setInsercao] = useState<number | null>(null);
  const [anuncio, setAnuncio] = useState('');

  useEffect(() => () => {
    if (animacaoRef.current !== null) cancelAnimationFrame(animacaoRef.current);
  }, []);

  useEffect(() => {
    const destino = focoDestinoRef.current;
    if (destino === null) return;
    focoDestinoRef.current = null;
    listaRef.current?.querySelectorAll<HTMLButtonElement>('.parcel-drag-handle')[destino]?.focus({ preventScroll: true });
  }, [parcelas]);

  function linhas() {
    return Array.from(listaRef.current?.querySelectorAll<HTMLElement>('[data-parcela-numero]') || []);
  }

  function atualizarDestino(arraste: Arraste) {
    const itens = linhas();
    const primeiro = itens[0]?.getBoundingClientRect();
    const ultimo = itens.at(-1)?.getBoundingClientRect();
    const dentro = primeiro && ultimo && arraste.x >= primeiro.left && arraste.x <= primeiro.right
      && arraste.y >= primeiro.top - 32 && arraste.y <= ultimo.bottom + 32;
    let destino: number | null = null;
    if (dentro) {
      destino = itens.findIndex(item => {
        const rect = item.getBoundingClientRect();
        return arraste.y < rect.top + rect.height / 2;
      });
      if (destino === -1) destino = itens.length;
    }
    arraste.insercao = destino;
    setInsercao(destino);
  }

  function rolarDuranteArraste() {
    const arraste = arrasteRef.current;
    if (!arraste?.ativo) return;
    const limite = 64;
    const deslocamento = arraste.y < limite ? -12 : arraste.y > window.innerHeight - limite ? 12 : 0;
    if (deslocamento) {
      window.scrollBy(0, deslocamento);
      atualizarDestino(arraste);
    }
    animacaoRef.current = requestAnimationFrame(rolarDuranteArraste);
  }

  function encerrarArraste() {
    const arraste = arrasteRef.current;
    arrasteRef.current = null;
    if (animacaoRef.current !== null) cancelAnimationFrame(animacaoRef.current);
    animacaoRef.current = null;
    if (arraste?.botao.hasPointerCapture(arraste.pointerId)) arraste.botao.releasePointerCapture(arraste.pointerId);
    setArrastada(null);
    setInsercao(null);
  }

  function mover(numero: number, destino: number) {
    if (desabilitado) return;
    const origem = parcelas.findIndex(parcela => parcela.numero === numero);
    const ordenadas = reordenarParcelas(parcelas, origem, destino);
    if (ordenadas === parcelas) return;
    focoDestinoRef.current = destino;
    onChange(ordenadas);
    setAnuncio(`Parcela ${numero} movida para a posição ${destino + 1} de ${parcelas.length}.`);
  }

  function iniciar(e: PointerEvent<HTMLButtonElement>, numero: number) {
    if (desabilitado || parcelas.length < 2 || !e.isPrimary || e.button !== 0) return;
    e.preventDefault();
    e.currentTarget.focus({ preventScroll: true });
    e.currentTarget.setPointerCapture(e.pointerId);
    arrasteRef.current = {
      numero, pointerId: e.pointerId, inicioY: e.clientY, x: e.clientX, y: e.clientY,
      ativo: false, insercao: null, botao: e.currentTarget,
    };
  }

  function arrastar(e: PointerEvent<HTMLButtonElement>) {
    const arraste = arrasteRef.current;
    if (!arraste || e.pointerId !== arraste.pointerId) return;
    arraste.x = e.clientX;
    arraste.y = e.clientY;
    if (!arraste.ativo && Math.abs(e.clientY - arraste.inicioY) < 4) return;
    e.preventDefault();
    if (!arraste.ativo) {
      arraste.ativo = true;
      setArrastada(arraste.numero);
      animacaoRef.current = requestAnimationFrame(rolarDuranteArraste);
    }
    atualizarDestino(arraste);
  }

  function soltar(e: PointerEvent<HTMLButtonElement>) {
    const arraste = arrasteRef.current;
    if (!arraste || e.pointerId !== arraste.pointerId) return;
    if (arraste.ativo && !desabilitado) {
      arraste.x = e.clientX;
      arraste.y = e.clientY;
      atualizarDestino(arraste);
      const origem = parcelas.findIndex(parcela => parcela.numero === arraste.numero);
      if (arraste.insercao !== null) mover(arraste.numero, destinoDaInsercao(origem, arraste.insercao));
    }
    encerrarArraste();
  }

  function teclado(e: KeyboardEvent<HTMLButtonElement>, numero: number) {
    if (e.key === 'Escape') {
      encerrarArraste();
      return;
    }
    if (arrasteRef.current || !['ArrowUp', 'ArrowDown'].includes(e.key)) return;
    e.preventDefault();
    const origem = parcelas.findIndex(parcela => parcela.numero === numero);
    mover(numero, origem + (e.key === 'ArrowUp' ? -1 : 1));
  }

  return {
    listaRef, anuncio,
    classeLinha(indice: number, numero: number) {
      const origem = parcelas.findIndex(parcela => parcela.numero === arrastada);
      const destinoValido = insercao !== null && destinoDaInsercao(origem, insercao) !== origem;
      return [
        'parcel-line', arrastada === numero ? 'parcel-dragging' : '',
        destinoValido && insercao === indice ? 'parcel-drop-before' : '',
        destinoValido && insercao === parcelas.length && indice === parcelas.length - 1 ? 'parcel-drop-after' : '',
      ].filter(Boolean).join(' ');
    },
    propsAlca(numero: number) {
      return {
        disabled: desabilitado || parcelas.length < 2,
        onPointerDown: (e: PointerEvent<HTMLButtonElement>) => iniciar(e, numero),
        onPointerMove: arrastar,
        onPointerUp: soltar,
        onPointerCancel: encerrarArraste,
        onLostPointerCapture: encerrarArraste,
        onKeyDown: (e: KeyboardEvent<HTMLButtonElement>) => teclado(e, numero),
      };
    },
  };
}
