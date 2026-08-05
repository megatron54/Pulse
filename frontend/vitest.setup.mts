import "@testing-library/jest-dom/vitest";

// jsdom no implementa ResizeObserver - lo necesita `recharts`
// (ResponsiveContainer) para medir el contenedor. Polyfill mínimo
// suficiente para que los componentes de gráficas rendericen en tests
// sin necesitar un tamaño real de layout.
class ResizeObserverPolyfill {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserverPolyfill;

// jsdom no calcula layout real: todo elemento mide 0x0, lo que hace que
// `ResponsiveContainer` de recharts rehúse renderizar ("width(0) and
// height(0)..."). Se fuerza un tamaño fijo razonable solo en el entorno
// de test - no afecta al layout real del navegador.
Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
  configurable: true,
  value: 300,
});
Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
  configurable: true,
  value: 200,
});
Element.prototype.getBoundingClientRect = () =>
  ({
    width: 300,
    height: 200,
    top: 0,
    left: 0,
    right: 300,
    bottom: 200,
    x: 0,
    y: 0,
    toJSON() {},
  }) as DOMRect;
