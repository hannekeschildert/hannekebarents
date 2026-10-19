# hannekebarents.nl

Website voor kunstschilder Hanneke Barents: schilderijen (met "te koop" / "verkocht"), nieuws/blog, over en contact. Geen webwinkel; bezoekers sturen een e-mail.

Hosting en onderhoud zijn gratis: de site draait op GitHub Pages en wordt bijgewerkt via Pages CMS, een invulscherm waarin Hanneke schilderijen en berichten kan toevoegen zonder iets van code te weten.

## Nederlands en Engels

De site is in het Nederlands (`hannekebarents.nl`). Rechtsboven staat een klein vlaggetje: een klik op de Britse vlag opent de Engelse versie (`hannekebarents.nl/en/`), en daar staat de Nederlandse vlag om terug te gaan.

In het invulscherm staan onder de Nederlandse velden de velden "in het Engels (mag leeg blijven)". Wordt een Engelse tekst niet ingevuld, dan toont de Engelse versie de Nederlandse tekst met de opmerking dat die alleen in het Nederlands beschikbaar is. Titels en technieken zonder vertaling blijven gewoon Nederlands staan.

## Wat is voorbeeldinhoud?

Alles. De 8 "Voorbeeld"-schilderijen zijn abstracte plaatjes, geen echt werk. De teksten bij Over, Contact en Nieuws zijn invultekst. Het e-mailadres in `data/site.json` is leeg. Vul het in voordat de site live gaat.

## Online zetten (eenmalig, ongeveer 30 minuten)

1. **GitHub-account.** Maak een gratis account op github.com en maak een nieuwe repository, bijvoorbeeld `hannekebarents`, met zichtbaarheid **Public** (gratis Pages werkt alleen met een publieke repository).
2. **Bestanden uploaden.** Kies in de repository *Add file → Upload files* en sleep de inhoud van deze map erin (niet de map zelf). Controleer daarna of de map `.github` er is. Zo niet, kies *Add file → Create new file*, noem het bestand `.github/workflows/deploy.yml` en plak de inhoud van `deploy-workflow.txt`.
3. **Pages aanzetten.** Ga naar *Settings → Pages* en kies bij *Source* voor **GitHub Actions**. Na een minuut of twee is de site te zien op `jouwnaam.github.io/hannekebarents`. (Via *Actions* kun je de voortgang volgen.)
4. **Eigen domein koppelen.** Vul bij *Settings → Pages → Custom domain* `hannekebarents.nl` in. Zet daarna bij de registrar waar het domein is gekocht deze DNS-records:
   - vier **A**-records voor `@` (of leeg/het hoofddomein): `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - een **CNAME**-record voor `www` naar `jouwnaam.github.io`
   - verwijder eventuele standaard-records die de registrar zelf had toegevoegd
5. **HTTPS.** Wacht tot de DNS-wijziging is doorgekomen (tot 24 uur) en zet daarna *Enforce HTTPS* aan in *Settings → Pages*.

## Zelf bijhouden door Hanneke (Pages CMS)

1. Ga naar **app.pagescms.org** en log in met GitHub. Kies de repository.
2. Links staan: *Schilderijen*, *Nieuws en blog*, *Over*, *Contact* en *Naam en contactgegevens*.
3. Een schilderij toevoegen: *Schilderijen → nieuw*, foto kiezen, titel en gegevens invullen, opslaan. Na ongeveer een à twee minuten staat het op de site.
4. Foto's mogen groot zijn (rechtstreeks van de telefoon). De site maakt ze automatisch kleiner.

Hanneke heeft hiervoor een eigen (gratis) GitHub-account nodig. Voeg haar toe via *Settings → Collaborators* in de repository.

Vul meteen onder *Naam en contactgegevens* het e-mailadres in.

## Zelf lokaal bekijken (optioneel)

Vereist Python 3.

```
pip install -r requirements.txt
python build.py
python -m http.server -d _site 8000
```

Open dan http://localhost:8000.

## Mappen

- `content/schilderijen`, `content/nieuws`, `content/pagina`: de teksten (een bestand per schilderij of bericht)
- `media/`: de foto's
- `data/site.json`: naam, e-mailadres, Instagram enzovoort
- `templates/` en `static/`: uiterlijk van de site
- `build.py`: bouwt alles tot een website (`_site/`)
- `.pages.yml`: instellingen voor het invulscherm
