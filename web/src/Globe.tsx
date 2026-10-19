import {
  Cartesian2,
  Cartesian3,
  Color,
  ConstantPositionProperty,
  EllipsoidTerrainProvider,
  ImageryLayer,
  OpenStreetMapImageryProvider,
  Viewer,
} from "cesium";
import { useEffect, useRef } from "react";
import { llaAt, sampleTrack } from "./orbit/geo";
import type { Pass } from "./orbit/pass";
import { NAIROBI } from "./orbit/station";
import type { ParsedTle } from "./orbit/tle";

type Props = {
  name: string;
  tle: ParsedTle | null;
  pass: Pass | null;
};

const ORBIT_MS = 92 * 60 * 1000;
const ORBIT_STEP_MS = 30_000;
const PASS_STEP_MS = 5_000;

function cart(lla: { latitudeDeg: number; longitudeDeg: number; heightKm: number }) {
  return Cartesian3.fromDegrees(
    lla.longitudeDeg,
    lla.latitudeDeg,
    lla.heightKm * 1000,
  );
}

export default function Globe({ name, tle, pass }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Viewer | null>(null);

  useEffect(() => {
    const el = host.current;
    if (!el) {
      return;
    }
    const viewer = new Viewer(el, {
      baseLayer: new ImageryLayer(
        new OpenStreetMapImageryProvider({
          url: "https://tile.openstreetmap.org/",
        }),
      ),
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      sceneModePicker: false,
      selectionIndicator: false,
      timeline: false,
      animation: false,
      navigationHelpButton: false,
      terrainProvider: new EllipsoidTerrainProvider(),
    });
    viewer.scene.globe.enableLighting = true;
    viewer.entities.add({
      name: "Nairobi",
      position: Cartesian3.fromDegrees(
        NAIROBI.longitudeDeg,
        NAIROBI.latitudeDeg,
        0,
      ),
      point: { pixelSize: 10, color: Color.WHITE },
      label: {
        text: "Nairobi",
        font: "14px sans-serif",
        fillColor: Color.WHITE,
        pixelOffset: new Cartesian2(0, -16),
        showBackground: true,
      },
    });
    viewerRef.current = viewer;
    return () => {
      viewer.destroy();
      viewerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) {
      return;
    }
    const extras = viewer.entities.values.filter((e) => e.name !== "Nairobi");
    for (const entity of extras) {
      viewer.entities.remove(entity);
    }
    if (!tle) {
      return;
    }
    const now = new Date();
    const orbit = sampleTrack(tle, new Date(now.getTime() - 10 * 60_000), ORBIT_MS, ORBIT_STEP_MS);
    viewer.entities.add({
      name: "orbit",
      polyline: {
        positions: orbit.map(cart),
        width: 2,
        material: Color.CYAN.withAlpha(0.55),
      },
    });
    if (pass) {
      const windowTrack = sampleTrack(
        tle,
        pass.rise,
        pass.set.getTime() - pass.rise.getTime(),
        PASS_STEP_MS,
      );
      viewer.entities.add({
        name: "contact",
        polyline: {
          positions: windowTrack.map(cart),
          width: 4,
          material: Color.YELLOW,
        },
      });
    }
    const sat = viewer.entities.add({
      name: "sat",
      position: cart(llaAt(tle, now)),
      point: { pixelSize: 12, color: Color.YELLOW },
      label: {
        text: name,
        font: "13px sans-serif",
        fillColor: Color.YELLOW,
        pixelOffset: new Cartesian2(0, -16),
        showBackground: true,
      },
    });
    const id = window.setInterval(() => {
      if (viewer.isDestroyed()) {
        return;
      }
      sat.position = new ConstantPositionProperty(cart(llaAt(tle, new Date())));
    }, 1000);
    return () => window.clearInterval(id);
  }, [tle, pass, name]);

  return <div ref={host} className="globe" aria-label="Earth globe with satellite track" />;
}
