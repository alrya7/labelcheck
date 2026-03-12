"use client";

import { useState, useRef, useCallback, useEffect } from "react";

export default function LabelImageViewer({ src }: { src: string }) {
  const [scale, setScale] = useState(1);
  const [dragging, setDragging] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const dragStart = useRef({ x: 0, y: 0 });
  const posStart = useRef({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault();
    setScale((s) => Math.max(0.5, Math.min(5, s - e.deltaY * 0.002)));
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (scale <= 1) return;
      setDragging(true);
      dragStart.current = { x: e.clientX, y: e.clientY };
      posStart.current = { ...pos };
    },
    [scale, pos]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragging) return;
      setPos({
        x: posStart.current.x + e.clientX - dragStart.current.x,
        y: posStart.current.y + e.clientY - dragStart.current.y,
      });
    },
    [dragging]
  );

  const handleMouseUp = useCallback(() => setDragging(false), []);

  const resetView = useCallback(() => {
    setScale(1);
    setPos({ x: 0, y: 0 });
  }, []);

  return (
    <div className="border rounded-lg overflow-hidden bg-white">
      <div className="bg-gray-50 px-4 py-3 flex justify-between items-center">
        <h3 className="font-semibold">Макет этикетки</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setScale((s) => Math.max(0.5, s - 0.25))}
            className="px-2 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300"
          >
            -
          </button>
          <span className="text-sm text-gray-600 w-14 text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => setScale((s) => Math.min(5, s + 0.25))}
            className="px-2 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300"
          >
            +
          </button>
          <button
            onClick={resetView}
            className="px-2 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300"
          >
            Сброс
          </button>
        </div>
      </div>
      <div
        ref={containerRef}
        className="relative overflow-hidden bg-gray-100 flex items-center justify-center"
        style={{ height: "600px", cursor: scale > 1 ? (dragging ? "grabbing" : "grab") : "default" }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <img
          src={src}
          alt="Этикетка"
          draggable={false}
          className="select-none max-w-full max-h-full"
          style={{
            transform: `translate(${pos.x}px, ${pos.y}px) scale(${scale})`,
            transformOrigin: "center center",
            objectFit: "contain",
          }}
        />
      </div>
      <div className="bg-gray-50 px-4 py-2 text-xs text-gray-500 text-center">
        Колёсико мыши — масштаб. Перетаскивание при увеличении.
      </div>
    </div>
  );
}
