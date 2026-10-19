import { V2_STATUS } from "./v2";

export default function App() {
  return (
    <main>
      <p className="kicker">OrbitLog</p>
      <h1>Ride along with a real satellite and watch it think.</h1>
      <p>
        This app will show a live orbit and the next contact window over
        Nairobi. Satellites only talk to the ground for a few minutes, a few
        times a day. Diagnosing faults onboard is how a useful report still
        fits through that window.
      </p>
      <p>
        v1 (this track) is real TLEs and SGP4 passes. The globe lands in a
        later sprint. v2, the onboard diagnosis story, is{" "}
        <strong>{V2_STATUS}</strong> until the benchmark writes files under{" "}
        <code>results/</code>. This page will never invent those numbers.
      </p>
      <p className="note">
        Faults in OrbitLog are simulated on a ground Linux box, not live
        satellite telemetry.
      </p>
    </main>
  );
}
