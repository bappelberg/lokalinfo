"use client";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white text-gray-900 px-6 py-12 flex justify-center">
      <div className="max-w-3xl w-full space-y-10">

        {/* Titel */}
        <div>
          <h1 className="text-3xl font-bold mb-2">🗺️ LokalInfo</h1>
          <p className="text-gray-600 text-lg">
            Din karta över vad som händer just nu
          </p>
        </div>

        {/* Intro */}
        <section className="space-y-3">
          <p>
            LokalInfo är en interaktiv kartbaserad app där människor delar vad som händer i deras närområde – i realtid.
          </p>
          <p>
            Oavsett om det gäller trafikproblem, händelser, faror eller tips, får du en snabb och visuell överblick direkt på kartan.
          </p>
        </section>

        {/* Upptäck */}
        <section>
          <h2 className="text-xl font-semibold mb-2">📍 Upptäck lokala händelser</h2>
          <p className="text-gray-700">
            Se inlägg placerade exakt där de sker. Varje markör på kartan representerar en händelse – från olyckor och störningar till restaurangtips och evenemang.
          </p>
        </section>

        {/* Live & historik */}
        <section>
          <h2 className="text-xl font-semibold mb-2">⚡ Live & historik</h2>
          <ul className="list-disc pl-5 text-gray-700 space-y-1">
            <li><strong>Live-läge:</strong> Följ vad som händer just nu, uppdaterat var 30:e sekund</li>
            <li><strong>Historik:</strong> Res tillbaka upp till 30 dagar och se vad som hänt tidigare</li>
          </ul>
        </section>

        {/* Dela */}
        <section>
          <h2 className="text-xl font-semibold mb-2">📝 Dela själv</h2>
          <ul className="list-disc pl-5 text-gray-700 space-y-1">
            <li>Lägg ut inlägg direkt på kartan</li>
            <li>Välj kategori (t.ex. trafik, brott, event, mat)</li>
            <li>Lägg till bild och beskrivning</li>
          </ul>
        </section>

        {/* Rösta */}
        <section>
          <h2 className="text-xl font-semibold mb-2">👍 Rösta & påverka</h2>
          <ul className="list-disc pl-5 text-gray-700 space-y-1">
            <li>Upvotes och downvotes påverkar synlighet</li>
            <li>Viktigare händelser blir större och mer framträdande på kartan</li>
            <li>Hjälp communityn att filtrera fram det som är relevant</li>
          </ul>
        </section>

        {/* Kommentarer */}
        <section>
          <h2 className="text-xl font-semibold mb-2">💬 Diskutera i trådar</h2>
          <ul className="list-disc pl-5 text-gray-700 space-y-1">
            <li>Diskutera händelsen</li>
            <li>Svara på varandra i trådar</li>
            <li>Rösta på kommentarer</li>
          </ul>
        </section>

        {/* Snabb överblick */}
        <section>
          <h2 className="text-xl font-semibold mb-2">📲 Snabb överblick</h2>
          <ul className="list-disc pl-5 text-gray-700 space-y-1">
            <li>Horisontell “Senaste nytt”-feed längst ner</li>
            <li>Klicka för att flyga direkt till platsen på kartan</li>
            <li>Smidig navigation mellan inlägg</li>
          </ul>
        </section>

        {/* Sök */}
        <section>
          <h2 className="text-xl font-semibold mb-2">🔍 Sök & navigera</h2>
          <ul className="list-disc pl-5 text-gray-700 space-y-1">
            <li>Sök efter adresser eller platser</li>
            <li>Hoppa direkt till valfri plats i kartan</li>
          </ul>
        </section>

        {/* Rapportering */}
        <section>
          <h2 className="text-xl font-semibold mb-2">🚨 Rapportera innehåll</h2>
          <ul className="list-disc pl-5 text-gray-700 space-y-1">
            <li>Rapportera olämpliga inlägg</li>
            <li>Community-driven moderering</li>
          </ul>
        </section>

        {/* Varför */}
        <section>
          <h2 className="text-xl font-semibold mb-2">🎯 Varför LokalInfo?</h2>
          <ul className="list-disc pl-5 text-gray-700 space-y-1">
            <li>Hyperlokal information – där du faktiskt befinner dig</li>
            <li>Realtidsuppdateringar</li>
            <li>Community-driven innehåll</li>
            <li>Enkelt, snabbt och visuellt</li>
          </ul>
        </section>

      </div>
    </div>
  );
}