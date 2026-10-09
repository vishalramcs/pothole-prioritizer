"use client";

import { createLeafletContext, LeafletContext, type LeafletContextInterface } from "@react-leaflet/core";
import L from "leaflet";
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

/** react-leaflet's <MapContainer>, but the Leaflet map lives exactly as long as the page is shown.
 * With cacheComponents, Next keeps visited pages alive but hidden (React Activity): hiding runs effect
 * cleanups, and MapContainer then destroys its map while keeping it in state, so coming back crashed
 * ("Map container is being reused"). Here hide removes the map and show builds a new one. */
export default function LiveMap({ center, zoom, className, scrollWheelZoom = true, children }: {
  center: [number, number];
  zoom: number;
  className?: string;
  scrollWheelZoom?: boolean;
  children: ReactNode;
}) {
  const div = useRef<HTMLDivElement>(null);
  const [ctx, setCtx] = useState<LeafletContextInterface | null>(null);
  const initial = useRef({ center, zoom, scrollWheelZoom }); // like MapContainer: props are read once per map

  useLayoutEffect(() => {
    const map = L.map(div.current!, { scrollWheelZoom: initial.current.scrollWheelZoom })
      .setView(initial.current.center, initial.current.zoom);
    setCtx(createLeafletContext(map));
    return () => {
      setCtx(null);
      map.remove();
    };
  }, []);

  return (
    <div ref={div} className={className}>
      {ctx && <LeafletContext value={ctx}>{children}</LeafletContext>}
    </div>
  );
}
