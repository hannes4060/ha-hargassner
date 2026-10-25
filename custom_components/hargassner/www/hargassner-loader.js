/*
 * Ladeskript für die Hargassner-Karte.
 *
 * Die Integration kopiert diese Datei nach /config/www/hargassner/ und trägt sie
 * als Lovelace-Ressource ein (/local/...). /local stellt Home Assistant sofort beim
 * Start bereit, die eigentliche Karte unter /hargassner/ dagegen erst, wenn die
 * Integration geladen ist. Lädt das Dashboard in dieser Startphase, schlägt der
 * erste Versuch fehl; das Skript versucht es dann alle 2 Sekunden erneut.
 * Sobald die Karte definiert ist, baut Home Assistant sie automatisch neu auf.
 */
const version = new URL(import.meta.url).searchParams.get("v") || "0";
const src = `/hargassner/hargassner-card.js?v=${encodeURIComponent(version)}`;

async function load(attempt = 0) {
  if (customElements.get("hargassner-card")) return;
  try {
    // Fehlgeschlagene Modul-Importe merkt sich der Browser pro URL,
    // daher bekommt jeder neue Versuch eine eigene URL.
    await import(attempt ? `${src}&r=${attempt}` : src);
  } catch (err) {
    if (attempt < 150) {
      setTimeout(() => load(attempt + 1), 2000);
    } else {
      console.error("hargassner-card: Karte konnte nicht geladen werden", err);
    }
  }
}

load();
