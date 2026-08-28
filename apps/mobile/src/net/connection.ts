/**
 * What the handset itself says about its connection.
 *
 * This exists for one reason: a fetch that fails gives the same JavaScript
 * error whether the server is off or the phone is on mobile data, and the
 * spec's edge cases require those two be told apart — "the fix is different"
 * (spec 001, Edge Cases). One means go and start the server; the other means
 * go and change Wi-Fi. A single "cannot connect" message would send the reader
 * to the wrong one half the time.
 *
 * ## What this can and cannot tell you
 *
 * It reads the transport the OS is currently using. That reliably separates
 * "no connection / mobile data" from "on a Wi-Fi network".
 *
 * It does NOT know WHICH Wi-Fi network. A phone on a neighbour's Wi-Fi, or on
 * a guest VLAN that cannot see the laptop, reports `home-network-possible` and
 * will be told the server is unreachable. Reading the SSID needs a location
 * permission on both platforms, which is a large ask for a slightly better
 * error message, so the classification is deliberately named for what it
 * actually knows: the home network is *possible*, not confirmed.
 */
import * as Network from "expo-network";

export type Reachability =
  /** On Wi-Fi, Ethernet or a VPN — the home server could be on the other end. */
  | "home-network-possible"
  /** No connection, or a transport that cannot see the house: mobile data. */
  | "off-home-network"
  /** The platform would not say. Web reports this; so does Android sometimes. */
  | "unknown";

export async function probeConnection(): Promise<Reachability> {
  let state: Network.NetworkState;
  try {
    state = await Network.getNetworkStateAsync();
  } catch {
    // Never let the diagnostic be the thing that crashes the screen: an
    // unknown connection still produces a usable message downstream.
    return "unknown";
  }

  if (state.isConnected === false) return "off-home-network";

  switch (state.type) {
    case Network.NetworkStateType.WIFI:
    case Network.NetworkStateType.ETHERNET:
    // VPN counts as possible on purpose: ADR-0013 makes Tailscale the intended
    // way to reach this system from outside the house, and FW_HOST is allowed
    // to be a MagicDNS name.
    case Network.NetworkStateType.VPN:
      return "home-network-possible";

    case Network.NetworkStateType.NONE:
    case Network.NetworkStateType.CELLULAR:
    case Network.NetworkStateType.BLUETOOTH:
    case Network.NetworkStateType.WIMAX:
    case Network.NetworkStateType.OTHER:
      return "off-home-network";

    default:
      // NetworkStateType.UNKNOWN, and `type` is optional in the API so it can
      // also be absent entirely.
      return "unknown";
  }
}
