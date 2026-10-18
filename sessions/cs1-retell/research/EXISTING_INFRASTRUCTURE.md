# Existing government and first-responder infrastructure: what DIZA should copy, integrate with, or mention

- **Session:** cs1-retell (research subagent), 2026-10-17
- **Scope:** 911/NG911, 311/211, public alerts, incident management, commercial products, and legal/compliance, as they apply to DIZA (a community/211-style AI phone line, not a PSAP).
- **Method:** web search plus direct reads of primary documents where possible. The NENA call-processing standard (NENA-STA-020.2-2026) was downloaded and read in full text. The NWS alerts API was called live.
- **Verification key:** **[V]** means checked against an official or primary source. **[S]** means a secondary source only (news, vendor, law firm). **[UNVERIFIED]** means not confirmed, so don't put it on a slide as fact.

---

## (a) One-page summary

1. **NENA now explicitly allows AI on non-emergency lines, which is our strongest pitch fact.** The 2026 NENA 9-1-1 Call Processing Standard, §5.6.2, says: *"Agencies can improve operations by supplementing PSAP call processing with artificial intelligence platforms to divert non-emergency calls … Systems should validate the call is non-emergency. Ideally, the system should detect an emergency situation and redirect the caller appropriately."* That is DIZA's design: detect P0, tell the caller to call 911, and handle everything else. **[V]** ([NENA-STA-020.2-2026 PDF](https://cdn.ymaws.com/www.nena.org/resource/resmgr/standards/standards1/NENA-STA-020.2-2026_911CallP.pdf))
2. **We should copy several NENA rules directly:**
   - Ask and verify location first (§4.1.2).
   - Call back abandoned calls at least once, in the same mode they came in, and be careful where repeated callbacks could put the caller at risk (§5.4, §5.4.1).
   - Evaluate every duplicate call on its own merits even when it is clustered (§5.5.6).
   - Give callers access to translation (§5.5.5).
   - Measure answer time against 90% within 15 s and 95% within 20 s (§4.1).
   
   All **[V]** from the same PDF.
3. **911 surge reality in LA:** residents reported busy signals during the January 2025 Palisades fire and long 911 waits. **[S]** ([Westside Current](https://www.westsidecurrent.com/news/more-calls-longer-waits-l-a-residents-report-alarming-delays-in-911/article_01710a42-57a1-46d6-80de-551703582ada.html)) 211 LA logged 42,000+ wildfire-related contacts from 7 January 2025. **[V]** ([211la.org](https://211la.org/211-la-wildfire-response)) The non-emergency load during a disaster is real, and DIZA takes it off 911.
4. **Location is the main gap.** 911 receives carrier location (Phase II) and device-based hybrid location (AML/RapidSOS) automatically. DIZA only gets what the caller says. The fix that fits a hackathon is copied from Carbyne's c-Lite: **text the caller a one-time browser link that shares GPS (and optionally a photo)**, with no app needed. **[S]** ([Vonage/Carbyne](https://www.vonage.com/resources/customers/carbyne/))
5. **Alerts in LA are set by four facts:**
   - Alert LA County runs on **Genasys ALERT**. Its channels are mobile push, IPAWS, text, email, voice, social, XML, CAP and speakers. **[V vendor PR]** ([Genasys PR, 7 Nov 2024](https://genasys.com/press-releases/los-angeles-county-adds-genasys-alert-emergency-warning-and-notification-to-genasys-evac-emergency-management-and-planning/))
   - Evacuation zones live on **Genasys Protect** (protect.genasys.com). **[V]** ([lacounty.gov/emergency](https://lacounty.gov/emergency/))
   - NotifyLA (City of LA) geotargets phone, text and email. Landlines are loaded automatically from 911 data, but cell numbers must register. **[V]** ([emergency.lacity.gov/notifyla](https://emergency.lacity.gov/notifyla))
   - On 9 January 2025 a Kenneth Fire evacuation warning reached about 10 million people countywide. A congressional report blamed a Genasys location-coding issue. **[S]** ([CBS](https://www.cbsnews.com/news/los-angeles-wildfires-evacuation-alerts-genasys/), [Insurance Journal](https://amp.insurancejournal.com/news/west/2025/05/15/823791.htm))
   
   The lesson for DIZA is that **human approval and an explicit target zone check before any batch call** belong in the pitch.
6. **Zone IDs are not "LAC-xxxx".** Zone IDs on LA County incident lists look like `LOS-0767-D`, `MAL-C111-A` and `MTN-U028-A`. **[S]** (county evacuation lists via [lacounty.gov/emergency](https://lacounty.gov/emergency/) search results) "LAC-" did not appear anywhere. Treat the ID format as **[UNVERIFIED]** and store it as free text.
7. **The data standards DIZA can claim are real and free:**
   - CAP 1.2 for alerts (IPAWS uses it). **[S]** ([NWS](https://www.weather.gov/documentation/tb-alerts-CAP-Supporting-360-Character-and-Spanish-WEA), [FEMA/APCO slides](https://techforum.apcointl.org/wp-content/uploads/2F-Witmer-FEMA-EmergencyAlerting.pdf))
   - Open311 GeoReport v2 for 311-type reports. **[S]** ([archived spec](https://webarchive.library.unt.edu/web/20170118233000mp_/http://wiki.open311.org/GeoReport_v2))
   - HSDS 3.0 for 211 resource directories. **[V]** ([Open Referral docs](https://openreferral.readthedocs.io/en/latest/))
   
   A live NWS alerts feed (`api.weather.gov/alerts/active?area=CA`) responded to a call on 2026-10-17. **[V]**
8. **Compliance has four parts:**
   - The TCPA "emergency purposes" exception covers calls *"made necessary in any situation affecting the health and safety of consumers"* (47 CFR 64.1200(f)(4)). The FCC reads it broadly, but it excludes anything commercial. **[S]**: the law-firm summaries quote the CFR, and eCFR was blocked from this sandbox.
   - California requires all-party consent to record (Penal Code §632 / §632.7). **[V statute text via Justia]**
   - US SMS from a 10-digit number needs A2P 10DLC registration, or unregistered messages are blocked. **[S Twilio]**
   - HIPAA doesn't apply because DIZA isn't a covered entity. **[V HHS]**
9. **Accessibility:**
   - LA County has accepted text-to-911 since December 2017 ("call if you can, text if you can't"). **[V]** ([LAFD](https://lafd.org/news/text-911-comes-los-angeles), [lacity.gov](https://lacity.gov/news/text-9-1-1-anywhere-la-county))
   - The FCC tells TTY users to dial 911 directly rather than going through 711. **[V FCC guide]**
   
   DIZA should say this verbally and in every SMS.
10. **Things we should not build:** CAD, ESInet/i3, EMD protocol licensing, WEA/IPAWS origination, and an AFN registry. We should **mention** these as the systems DIZA hands off to.

---

## (b) Capability table

| What they do | Who | Does DIZA have it | Recommendation |
|---|---|---|---|
| Automatic caller number + address (ANI/ALI) delivered to the call-taker | 911 PSAPs via carriers | Partly. Retell gives us the caller's number (from_number). There is no address database | Out of scope (ALI). Use from_number for callbacks |
| Wireless Phase II location (carrier, roughly 50–300 m) | Carriers to PSAPs (FCC 47 CFR 20.18) | No | Out of scope. Mention in pitch |
| Device-based hybrid location (AML / RapidSOS, phone GPS+Wi-Fi) | Apple/Google to RapidSOS to PSAPs | No | Out of scope for 911 data. **Build our own: an SMS location link** |
| Location link by SMS, browser shares GPS/video, no app | Carbyne c-Lite, Prepared | No | **Build (top priority)** |
| Live photo/video from the caller | Carbyne, Prepared | No | Build a photo upload on the same link page. Video is out of scope |
| Text-to-911 / RTT | PSAPs (LA County since 2017); carriers deliver | No (voice only) | Mention, and tell callers who can't speak to text 911. RTT: out of scope |
| NG911 i3 / ESInet (IP routing, multimedia, GIS routing) | State 911 (Cal OES), NENA i3 | No | Out of scope. Mention: our JSON/CAP outputs are i3-era friendly |
| Computer-aided dispatch (CAD) | PSAPs (LAFD, LAPD, LASD) | No. The dashboard is a "mini-CAD" for volunteers | Don't call it CAD. Mention "exports to CAD/EOC" as future work |
| Structured call-taker protocols (EMD/EFD/EPD; determinants Ω/A/B/C/D/E) | IAED/PowerPhone, PSAPs | Partly. We have our own P0–P3 triage | Mention. Map P0 to "redirect to 911", never claim to be EMD |
| Overflow/rollover to alternate PSAPs; High Impact Event procedures | PSAPs, state 911 plans | Partly. Callback offer at the concurrency cap, batch reserved concurrency | Build: a visible "surge mode" banner + stats. Mention NENA HIE |
| Abandoned-call callback (≥1 attempt, same modality) | PSAPs (NENA §5.4.1); "automatic abandoned callback" tech | Partly. Callbacks are scheduled, but not automatically for dropped calls | **Build:** automatic one-time callback on dropped/short calls, with a safety skip |
| Redundant-call handling (each call evaluated individually) | PSAPs (NENA §5.5.6) | Yes, through clustering | Copy NENA wording. Keep each call's data inside a cluster |
| Translation on calls | PSAPs via language lines; Prepared (AI translation) | Yes (EN/ES/KO/ZH natively) | Mention. This is a strength |
| Live transcription | Prepared Assist, Carbyne | Yes (Retell transcripts) | Mention |
| AI handling of non-emergency calls | Prepared AI Assistant (EN/ES); NENA §5.6.2 | Yes (core product) | **Mention, citing NENA §5.6.2** |
| Caller safety profiles (medical, household) | Rave Smart911 | No | Out of scope. At most an opt-in AFN flag (below) |
| 311 city service requests (app, web, phone, pin drop, photos) | City of LA MyLA311 | Partly. We have forms | Build an Open311 GeoReport v2-shaped export (no live LA API verified) |
| 211 disaster hotline (24/7, many languages, damage reports for the County) | 211 LA (activated by LA County OEM) | Partly | Integrate by warm transfer / referral. Shape resources as HSDS. Pitch: "211's overflow front door" |
| Open311 GeoReport v2 | Open311 community; many cities | No | **Build** a JSON export endpoint |
| HSDS (Open Referral) resource data | 211s, resource directories | No (custom resources.yaml) | Build: rename fields to HSDS service/location/phone |
| WEA (cell broadcast, 90/360 chars, EN/ES) | FEMA IPAWS + carriers; alerting authorities | No | Out of scope. Mention |
| EAS (broadcast) | FEMA/FCC, broadcasters | No | Out of scope |
| CAP 1.2 alert format | OASIS; IPAWS; NWS | No | **Build:** emit CAP XML for approved alerts; ingest the NWS feed |
| NotifyLA (City) mass notification | LA City EMD | No | Mention and refer: "sign up at NotifyLA". Vendor [UNVERIFIED] |
| Alert LA County (Genasys ALERT) | LA County OEM | No | Mention and refer: alert.lacounty.gov |
| Evacuation zones (Genasys Protect) | LA County + cities | No | Build: a zone field on reports/alerts + "look up your zone at protect.genasys.com". Public API [UNVERIFIED] |
| TrojansAlert (campus) | USC DPS (Nixle) | No | Mention. Refer non-USC people to text "TrojansAlert" to 888777 |
| NIMS/ICS, EOC common operating picture | FEMA NIMS, LA County OEM / LA City EOC | Partly. The dashboard map is a COP for volunteers | Build: a one-click situation summary in ICS terms. Mention |
| Public damage/needs reporting (Survey123 / Crowdsource Reporter / Hub) | Esri customers (state OEMs) | Partly. Forms by phone | Build a CSV/GeoJSON export that ArcGIS can import |
| Crowdsourced crisis map with SMS intake + vetting | Ushahidi | Yes (voice intake + clustering + human review) | Mention as prior art. We add voice + languages |
| CERT volunteers (trained neighborhood responders) | LAFD CERT (free in City of LA) | Partly. Human volunteers take warm transfers | Mention: CERT members are natural DIZA volunteers |
| AFN registry (voluntary, confidential) | LA County OEM via Alert LA County (formerly SNAP) | No | Out of scope as a registry. Build an opt-in AFN flag + welfare call-down list |
| Welfare checks | Police (LAPD non-emergency), APS, community groups | Yes (welfare-outbound agent) | Mention. Keep it consent-based |
| Mass notification with two-way confirmation | Everbridge, Rave, Genasys | Partly (batch calls + replies) | Mention: voice-native two-way, many languages |

---

## (c) Notes by area, with sources

### 1. 911 / NG911

**ANI/ALI and wireless location**
- 911 receives the caller's number and an address/location record. For wireless calls, Phase II means the carrier sends a location within accuracy limits. Handset-based carriers must place 67% of Phase II calls within 50 m and 90% within 150 m. Network-based carriers must place 67% within 100 m and 90% within 300 m. **[S]** These figures come from summaries of FCC orders ([FCC 01-296](https://apps.fcc.gov/edocs_public/attachmatch/FCC-01-296A1.pdf), [Urgent Comms](https://urgentcomm.com/?p=7691)). The authoritative rule is 47 CFR 20.18, which wasn't fetched here.
- Dispatchable location means a street address plus floor/unit, or a vertical (z-axis) location. Its requirements were phased in from 2021. **[V]** ([911.gov Dispatchable Location Requirements, Oct 2020](https://www.911.gov/assets/Dispatchable_Location_Requirements_Oct_2020.pdf))
- **Location-based routing (LBR):** under FCC 24-4 (January 2024), nationwide carriers had to route wireless 911 calls by device location from 13 November 2024. Non-nationwide carriers and RTT followed by 13 May 2026. **[S]** ([DA 24-259](https://docs.fcc.gov/public/attachments/DA-24-259A1.pdf), [TLP law summary](https://www.tlp.law/2024/03/15/fcc-establishes-lbr-compliance-dates/)) Whether the 2026 deadlines were extended is **[UNVERIFIED]**.

**Device-based hybrid location (AML / RapidSOS)**
- AML is built into iOS and Android. During an emergency call the phone works out its location from GPS, Wi-Fi and cell data and sends it in the background, with no app needed. **[V]** for the Australian government description ([triplezero.gov.au](https://triplezero.gov.au/triple-zero/How-to-Call-000/advanced-mobile-location)); **[S]** ([EENA infographic](https://prod.eena.org/wp-content/uploads/AML-Infographic.pdf))
- In the US, Apple (from iOS 12, 2018) sends device location to PSAPs through RapidSOS. **[S]** ([PhoneArena](https://www.phonearena.com/news/911-iPhone-iOS-12-precise-location-dispatch-RapidSOS_id105847))
- RapidSOS says its platform and Portal are free to PSAPs. Data comes from tech partners (Apple, Google, apps), and PSAPs view it through the RapidSOS Portal or a CAD integration. New integrations need location plus additional data. **[S vendor]** ([RapidSOS developer docs](https://developer.rapidsos.com/node/107), [TechCrunch](https://techcrunch.com/2021/07/27/rapidsos-ec1-business))
- **DIZA relevance:** sending data into RapidSOS needs a partner agreement and is meant for 911 data. That is out of scope and not appropriate for a non-PSAP line. Whether a 211-style line *could* become a RapidSOS data partner is **[UNVERIFIED]**.

**Text-to-911 and RTT**
- **LA County status:** text-to-911 launched across most of the county in December 2017. LASD said 77 law and fire agencies were equipped. The city of LA says it is available throughout LA County, is for emergencies only, and is meant for people who are deaf or hard of hearing or can't safely speak. **[V]** ([LAFD](https://lafd.org/news/text-911-comes-los-angeles), [lacity.gov](https://lacity.gov/news/text-9-1-1-anywhere-la-county), [LAPD release](https://lapdonline.org/?p=19474))
- **How it works:**
  - The sender needs a text plan, and texting doesn't work while roaming.
  - Location accuracy varies.
  - If text isn't available, the carrier sends a bounce-back telling the sender to make a voice call.
  - Don't use abbreviations or emojis.
  
  **[S]** ([Culver City](https://culvercitycrossroads.com/2019/03/06/text-to-9-1-1-call-if-you-can-text-if-you-cant/), [AP via Washington Times](https://www.washingtontimes.com/news/2017/dec/2/text-to-911-rolls-out-in-los-angeles-county/))
- **FCC:** carriers must deliver texts to PSAPs that request them. The FCC still recommends calling when possible ("call if you can, text if you can't"). **[V]** ([FCC text-to-911 PDF](https://Fcc.gov/sites/default/files/text-to-911_-_what_you_need_to_know.pdf)) The FCC consumer web page returned 403 to the fetch tool.
- **California:** in February 2022, Cal OES reported 436 of 437 PSAPs had text-to-911 deployed, 302 of them using web-based over-the-top solutions. **[V]** ([Cal OES 911 Advisory Board slides, Feb 2022](https://www.caloes.ca.gov/wp-content/uploads/PSC/Documents/9-1-1-Advisory-Board-Feb_22_V10.pdf))
- **RTT:** in 2016 the FCC began moving from TTY to RTT. RTT users can reach 911 and 711. In March 2021 the FCC Text-to-911 Registry started listing PSAPs that accept RTT. **[V]** ([FCC RTT](https://www.fcc.gov/real-time-text), [FCC registry release](https://www.fcc.gov/fcc-expands-text-911-registry-include-real-time-text))

**NG911 / i3 / ESInet**
- NG911 is an IP-based 911 system. The ESInet is its network, and NENA's i3 standard defines NG911 core services. NG911 lets PSAPs take text, images, video and data. **[S]** ([911.gov Cyber Risks to NG911](https://www.911.gov/assets/Cyber-Risks-to-Next-Generation-911.pdf), [StateTech](https://statetechmagazine.com/article/2019/09/esinets-help-public-safety-agencies-move-ng911-perfcon)) The 911.gov NG911 landing page returned 403.
- California chose Atos as its prime NG911 provider. **[S]** ([Techwire](https://www.techwire.net/news/emergency-services-seeks-statewide-text-to-911.html))

**CAD**
- NENA definition: CAD is a computer-based system that helps PSAP telecommunicators by automating selected dispatching and record-keeping tasks. **[V]** ([NENA KB](https://kb.nena.org/wiki/CAD_(Computer_Aided_Dispatch)))
- CAD-to-CAD exchange is fragmented. California FIRESCOPE recommends a common incident data format and cites the NENA/APCO Emergency Incident Data Exchange (EIDX). **[V]** ([FIRESCOPE whitepaper](https://firescope.caloes.ca.gov/ICS%20Documents/FIRESCOPE%20CAD-TO-CAD%20Typing%20Recommendation%20Executive%20Summary%20Whitepaper.pdf)) Federal context is in [NHTSA CAD Strategies 2023](https://www.911.gov/assets/NHTSA-CAD-Strategies-for-the-Future_Mar-2023_Final.pdf).

**Call-taker protocols (EMD/EFD/EPD)**
- MPDS determinant levels run from Omega and Alpha up to Echo. Alpha, Bravo and Omega generally mean basic life support (BLS); Charlie, Delta and Echo mean advanced life support (ALS). Echo is the only level assigned during Case Entry. **[S]** ([IAED Journal: determinant codes](https://iaedjournal.org/determinant-codes/))
- These protocols are proprietary and licensed, and they require certification. **[UNVERIFIED in detail]** DIZA must not imitate EMD pre-arrival instructions beyond public first-aid guidance from ready.gov or the CDC.

**Call overflow / rollover**
- **Contingency diversion:** calls go to alternate PSAPs when trunks are busy, a threshold is passed, or a PSAP fails. The rerouting should happen at the 911 routing layer (selective router or NGCS) and not to 10-digit lines. **[V state template]** ([Illinois State Police 911 template](https://isp.illinois.gov/Statewide911Division/GetFile/9281f441-8ed7-44ca-8cc2-3a6707a3a5cb))
- **NENA High Impact Events:** PSAPs should have defined HIE procedures. Routine surges such as concerts or tourism don't count as HIEs. HIE periods are excluded from benchmark reporting. **[V]** (NENA-STA-020.2-2026, §7)
- **Answer standard:** 90% of 911 calls answered within 15 s (SHALL) and 95% within 20 s (SHOULD), aligned with NFPA 1225. Order of answering: 911 calls first, then non-emergency, then admin lines. **[V]** (NENA §4.1, §4.1.1)

**Abandoned-call callback**
- NENA §5.4: telecommunicators *SHALL attempt to contact the caller … for all abandoned, disconnected, silent, or non-responsive 9-1-1 calls*. The standard also says repeated callbacks can put callers at risk in some situations. **[V]**
- NENA §5.4.1:
  - If a valid callback number exists, the telecommunicator SHOULD try to reach the caller at least once, in the same way the call came in (text, voice or TTY). A second attempt MAY be made.
  - Local policy decides whether to leave voicemail or texts.
  - "Automatic Abandoned Callback Technology" MAY be used.
  
  **[V]**
- **Other NENA items DIZA should copy:**
  - §4.1.2: *"Agencies SHALL ask and verify the location of the caller first."*
  - §5.5.5: telecommunicators SHOULD have access to foreign-language translation.
  - §5.5.6: redundant calls on the same incident SHALL each be evaluated as unique, capturing location, identity, callback number and nature of the emergency.
  
  **[V]**

### 2. Non-emergency: 311 and 211

**MyLA311 (City of LA)**
- MyLA311 runs as an app, a website and the 311 / (213) 473-3231 phone line. Residents use it for graffiti, potholes, bulky items and similar requests. It supports pin drops for places without a street address, request tracking, completion notices, ADA reports, chat and photo-based identification of the request type. **[V]** ([Mayor's office](https://mayor.lacity.gov/news/mayor-bass-announces-launch-new-myla311-system-make-la-cleaner-and-safer-improved-city), [CD3](https://cd3.lacity.gov/myla311)) **[S]** ([ABC7](https://abc7.com/post/los-angeles-311-city-upgrades-system-unveils-new-app-service-requests/16099411/))
- It covers City of LA jurisdiction only. County and state property aren't included. **[S]** ([Mid City West](https://www.midcitywest.org/myla311))
- **A public Open311 API for MyLA311 is [UNVERIFIED]; none was found.** DIZA should export in Open311 format, not claim a live integration.

**LAPD non-emergency**
- 1-877-ASK-LAPD (1-877-275-5273) handles loud parties, petty crimes, abandoned vehicles and other situations where nobody's life is in danger. The LAPD says that if you're unsure, call 911. **[V]** ([LAPD contact](https://www.lapdonline.org/contact-us/), [LAPD release](https://www.lapdonline.org/newsroom/implementation-of-a-new-police-non-emergency-phone-number-877-ask-lapd/))

**211 LA**
- 211 LA becomes the countywide disaster hotline when LA County OEM activates it. It runs 24/7 in 240+ languages. During disasters it gives evacuation route, shelter, FEMA registration and debris information, and **takes property damage reports on behalf of the County**. **[V]** ([211 LA disaster info](https://211la.org/services/HxN4oAn1eIEKwxLehLdnGw2FeQn6p6/general-disaster-information), [211 LA disaster role](https://211la.org/articles/211-la-plays-critical-role-local-la-county-disasters))
- From 7 January 2025 it logged 42,000+ wildfire-related calls, texts and online contacts and identified 54,000+ households through emergency intake. **[V]** ([211la.org wildfire response](https://211la.org/211-la-wildfire-response); the page has no date)
- **Out-of-county number:** a 2025 county listing shows (800) 708-6029. Older material shows (800) 339-6993, which is the number in DIZA's knowledge base. **[S]** ([LA County locator](https://locator.lacounty.gov/dcfs/Location/3173852/information-and-referral-federation-of-los-angeles-county-inc)) **Re-check on 211la.org before the demo.**
- **How 211s triage:** I&R programs are accredited against the Inform USA (formerly AIRS) Standards. These include Assessment & Referral and Crisis Intervention standards, and 211 calls are not to be sent to answering machines. **[S]** ([211 LifeLine](https://211lifeline.org/about.php), [Missouri PSC filing](https://efis.psc.mo.gov/Document/Display/34911)) Detailed triage criteria are **[UNVERIFIED]**.

**Data standards**
- **Open311 GeoReport v2** is frozen and final. It has six methods: list services, describe one service, POST a request, GET requests, GET one request, and token lookup. **[S]** ([archived spec](https://webarchive.library.unt.edu/web/20170118233000mp_/http://wiki.open311.org/GeoReport_v2), [federation.data.gov](https://federation.data.gov/open311))
- **HSDS (Open Referral) 3.0** is the exchange format for service, location and organization data in human-services directories. It is designed to complement existing systems rather than replace them. **[V]** ([Open Referral docs](https://openreferral.readthedocs.io/en/latest/), [HSDS about](https://openreferral.readthedocs.io/en/v2.0/hsds/about/))

### 3. Alerts

- **IPAWS / CAP:** FEMA IPAWS-OPEN authenticates CAP messages (OASIS CAP v1.2) and sends them out over EAS, WEA and other channels. **[S]** ([FEMA slides at APCO](https://techforum.apcointl.org/wp-content/uploads/2F-Witmer-FEMA-EmergencyAlerting.pdf), [National Academies](https://www.nationalacademies.org/read/24935/chapter/8))
- **WEA:**
  - Since the 2019 FCC rules, WEA allows 360 characters (90 remains the mandatory fallback) and Spanish-language messages. **[V]** ([NWS 360-char notice](https://www.weather.gov/documentation/tb-alerts-CAP-Supporting-360-Character-and-Spanish-WEA))
  - Alert types are National/Presidential, Imminent Threat, AMBER and Public Safety. WEA is free, needs no sign-up, and only Presidential alerts can't be turned off. **[V]** ([FCC WEA PDF](https://Fcc.gov/sites/default/files/Wireless_Emergency_Alerts_wea.pdf), [FEMA types of alerts](https://fema.gov/node/496861))
  - **Gap DIZA fills:** WEA supports EN/ES only, so Korean and Chinese speakers don't get an alert in their own language. Whether WEA has added more languages since 2023 is **[UNVERIFIED]**.
- **NotifyLA (City of LA):**
  - Sends free phone, text and email alerts, geotargeted.
  - Landlines are loaded automatically from 911 data. Cell, VoIP and email contacts must register.
  - Residents can give multiple contacts and addresses and set language preferences.
  - Delivery can fail because of power loss, line capacity or spam blocking.
  
  **[V]** ([emergency.lacity.gov/notifyla](https://emergency.lacity.gov/notifyla), [lacity.gov](https://lacity.gov/news/get-alerted-local-emergencies-notifyla)) **The vendor (Everbridge?) is [UNVERIFIED].**
- **Alert LA County:**
  - Sign-up is at alert.lacounty.gov.
  - Since a four-year contract announced on 7 November 2024, it runs on Genasys ALERT, which replaced the previous provider. LA County has used Genasys EVAC since 2022.
  - Channels are push, IPAWS, SMS, email, voice, social, XML, CAP, speakers and the Genasys Protect app.
  
  **[V]** ([lacounty.gov/emergency](https://lacounty.gov/emergency/), [Genasys PR](https://genasys.com/press-releases/los-angeles-county-adds-genasys-alert-emergency-warning-and-notification-to-genasys-evac-emergency-management-and-planning/))
  - **Correction for our own docs:** `sessions/planning-claude/REACH.md` says Genasys "needs a smartphone app", which is wrong because ALERT also sends SMS and voice. The PR doesn't mention two-way reporting by residents, so "one-way" is plausible but **[UNVERIFIED]**.
- **Genasys Protect zones:**
  - Residents type an address on protect.genasys.com to get their zone name and status, which updates in real time during incidents. Warnings and orders name zones alongside streets and intersections. **[V]** ([City of Calabasas](https://www.cityofcalabasas.com/government/public-safety-emergency-preparedness/emergency-evacuation-zones), [lacounty.gov/emergency](https://lacounty.gov/emergency/))
  - Zone ID examples from county incident lists: `LOS-0767-D`, `MAL-C111-A`, `MTN-U028-A`. **[S]** "LAC-xxxx" was not found. **[UNVERIFIED]**
  - Whether a public API exists is **[UNVERIFIED]**.
- **9 January 2025 false alert:** a Kenneth Fire evacuation warning meant for the Calabasas/West Hills area went to about 10 million people countywide. "Echo" alerts followed. A congressional report pointed to a Genasys location-coding problem with IPAWS. Genasys added a safeguard that flags alerts sent without a target area. **[S]** ([CBS](https://www.cbsnews.com/news/los-angeles-wildfires-evacuation-alerts-genasys/), [Insurance Journal](https://amp.insurancejournal.com/news/west/2025/05/15/823791.htm), [Rep. Garcia letter](https://robertgarcia.house.gov/sites/evo-subsites/robertgarcia.house.gov/files/evo-media-document/Quill%20-%20Letter%20%23L22476%20-%20Alerts%20oversight%20letter%20Genasys%20-%2002-02-2025%20%40%2002-19%20PM.pdf))
- **TrojansAlert (USC):**
  - Sends text and email. Students, faculty and staff are enrolled automatically.
  - Others text "TrojansAlert" to 888777 (Nixle). The list resets on 15 August each year.
  - USC DPS emergency numbers are 213-740-4321 (UPC) and 323-442-1000 (HSC).
  
  **[V]** ([USC DPS FAQ](https://dps.usc.edu/?p=9350), [USC emergency FAQ](https://www.usc.edu/emergency/frequently-asked-questions/))
- **NWS CAP feed:** `https://api.weather.gov/alerts/active?area=CA` returned GeoJSON alert features on 2026-10-17 (a User-Agent header is required). **[V]** (tested live)

### 4. Incident management

- **NIMS/ICS and the COP:** NIMS requires a common operating picture, meaning a shared overview of an incident that supports consistent, timely decisions by Incident Command / Unified Command and supporting agencies. ICS principles include common terminology, management by objectives, and information management. **[S]** ([FEMA IS-0552 ICS module](https://emilms.fema.gov/is_0552/groups/51.html), [PEMA ELG2300 handouts](https://www.pema.pa.gov/Preparedness/Training-Exercises/For-Students/Student-Manuals/ELG2300/Documents/ELG2300_Handouts.pdf)) The primary FEMA NIMS document was not fetched.
- **Damage/needs reporting:**
  - Oklahoma OEM had residents fill in a Survey123 web form, which took under 5 minutes and fed a public dashboard. **[V]** ([Esri ArcNews](https://www.esri.com/about/newsroom/arcnews/oklahoma-crowdsources-damage-assessments-to-kick-start-disaster-recovery))
  - Esri's damage-assessment solution collects public reports through ArcGIS Hub. **[V]** ([Esri](https://esri.com/en-us/industries/emergency-management/solutions/damage-assessment))
  - Crowdsource Reporter specifics are **[UNVERIFIED]**.
  - In LA County, 211 LA takes damage reports on the County's behalf (above).
- **CERT:**
  - LAFD created CERT, piloted in 1985–87 (sources disagree on the year).
  - Training is 17.5 hours over 7 weeks, free in the City of LA for anyone 18 or older.
  - Contact: lafdcert@lacity.org, 213-202-3136.
  - The program claims 60,000+ people trained.
  
  **[V]** ([LAFD CERT](https://lafd.org/join/volunteer/cert)) **[S]** ([cert-la.com](https://www.cert-la.com/page/17), [NPS thesis](https://calhoun.nps.edu/entities/publication/1720a795-b97c-4599-89d2-59f4d367cc21))
- **AFN registry:**
  - LA County OEM runs a voluntary, confidential registry for people with access and functional needs as part of Alert LA County. It was formerly called SNAP (Specific Needs Awareness Planning).
  - Registering does **not** guarantee priority response.
  - In 2025 the Board of Supervisors asked for a feasibility study of a mobility/disability evacuation database. The outcome is **[UNVERIFIED]**.
  
  **[V]** ([211 LA listing](https://211la.org/services/HxEd0EjqLCWN6vGLIp4Lnv7sqdP2Jd/functional-needs-registries), [BOS motion](https://file.lacounty.gov/SDSInter/bos/supdocs/201281.pdf))
- **Welfare checks:** in LA these go through the LAPD non-emergency line, Adult Protective Services, or community groups. DIZA's welfare call-down is consent-based outreach and must not be presented as a police welfare check.

### 5. Products in use

| Product | What it offers | What DIZA lacks | Source |
|---|---|---|---|
| **Carbyne (c-Lite / c-Live)** | PSAP texts the caller a link. The browser streams location (around 10 ft claimed) and one-way video, with chat. No app needed | Location link, photo/video | [Vonage case study](https://www.vonage.com/resources/customers/carbyne/), [Washoe County 2021](https://www.washoecounty.gov/technology/board_committees/911_response/2021/Files/012121/Item%2015%20-%20WC%20Carbyne%20c-Live%20Universe.pdf), [Fayette Co.](https://thecitizen.com/2018/09/30/fayette-rolls-out-soft-launch-of-new-e-911-technology/) **[S]** |
| **Prepared (Prepared Live / Assist; acquired by Axon in Sept 2025 [S])** | Real-time transcription + translation for 911 (vendor claims 33 audio / 140+ text languages, and elsewhere 200+), caller photo/video, AI assistant for non-emergency calls in EN/ES ("reduce non-emergency calls by 50%", a vendor claim) | Photo/video. Its AI non-emergency assistant is the closest competitor | [Prepared AI](https://prepared911.com/landing/ai-for-911), [translation](https://www.prepared911.com/solutions/translation), [AWS listing](https://aws.amazon.com/marketplace/pp/prodview-v6x5yk45x7ebm) **[S vendor]** |
| **RapidSOS (Portal / UNITE)** | Free PSAP portal showing device location + data from Apple, Google, apps and wearables | Device location (not obtainable by a non-PSAP) | [RapidSOS dev docs](https://developer.rapidsos.com/node/107) **[S]** |
| **Rave (Smart911, Rave Alert)** | Citizen safety profiles shown to 911 (medical, household, pets), verified phones, opt-in alerts | Pre-registered caller profiles | [Washoe 2025](https://www.washoecounty.gov/technology/board_committees/911_response/2025/Files/051525/Item%206%20-%20Smart%20911%20Presentation.pdf), [Jefferson City](https://jeffersoncitymo.gov/government/rave_alerts_and_smart911.php) **[S]** |
| **Everbridge** | Multi-channel geotargeted mass notification with two-way safety confirmation | Large-scale, multi-channel (we're voice-first) | [Everbridge data sheet](https://www.everbridge.com/wp-content/uploads/2023/04/BO-DS-EN-Mass-Notification.pdf) **[S]** |
| **Genasys (ALERT, EVAC, Protect)** | LA County alerts + evacuation zones (above) | Zones, IPAWS origination | Above **[V]** |
| **Ushahidi** | Open-source crowdsourced map from SMS/web/email with admin vetting (Kenya 2008, Haiti 2010) | We already have the voice equivalent | [Wikipedia](https://wikipedia.com/wiki/Ushahidi), [New Humanitarian](https://www.thenewhumanitarian.org/node/248708) **[S]** |

### 6. Legal / compliance

- **TCPA emergency purposes:**
  - 47 CFR 64.1200(f)(4) defines emergency purposes as calls *"made necessary in any situation affecting the health and safety of consumers."* The autodialer/prerecorded-voice consent rules don't apply to such calls. **[S]** ([Faegre Drinker](https://www.faegredrinker.com/en/insights/publications/2020/3/fcc-clarifies-application-of-tcpas-emergency-purposes-exception-amid-covid-19-pandemic), [Dorsey](https://www.dorsey.com/newsresources/publications/client-alerts/2020/03/fcc-narrows-the-tcpa-emergency)) eCFR blocked the fetch tool. Read the eCFR text directly before quoting it in a deck.
  - The FCC reads "emergency" broadly, but telemarketing and debt collection never qualify. **[S]**
  - In 2016 (Blackboard ruling) the FCC said schools may make automated calls and texts about student/faculty health and safety under the exception. **[S]** ([Kelley Drye tracker](https://www.kelleydrye.com/viewpoints/newsletters/tcpa-tracker/tcpa-tracker-august-2016.md))
  - The 2020 COVID ruling limited reliance on the exception to hospitals, health care providers, government, and parties acting under their express direction. **[S]**
  - **Implication:** DIZA is neither government nor a contracted provider. Alert batch calls should go **only to people who opted in** (prior express consent) and stay strictly about health and safety, with "say stop" opt-out. Treat the exception as a backstop, not the basis.
- **California recording:**
  - Penal Code §632 bans recording a confidential communication without the consent of all parties. §632.7 covers cellular and cordless calls.
  - Penalties go up to $2,500 per violation (or $10,000 for repeat offenders) plus civil liability.
  - DIZA's opening recording notice is the right control.
  
  **[V]** ([Justia CA Penal Code 632](https://law.justia.com/codes/california/code-pen/part-1/title-15/chapter-1-5/section-632)) **[S]** ([RCFP](https://www.rcfp.org/reporters-recording-guide/california/))
- **A2P 10DLC:**
  - Business SMS from US 10-digit numbers needs Brand + Campaign registration with The Campaign Registry. Twilio blocks unregistered messages (error 30034).
  - Alternatives are toll-free verified numbers or short codes.
  - Registration can take days, which is unrealistic during a hackathon. Use verified trial numbers or email.
  
  **[S]** ([Twilio 10DLC overview](https://pages.twilio.com/10DLC-HelpArticles-WW))
- **HIPAA:** it applies only to covered entities (health plans, clearinghouses, and providers who conduct standard transactions electronically) and their business associates. DIZA is none of these, so HIPAA does not apply unless a covered entity contracts DIZA as a business associate. **[V]** ([HHS: Are you a covered entity?](https://www.hhs.gov/guidance/document/are-you-covered-entity)) California's CMIA may still apply to medical information, but that is **[UNVERIFIED]** and was not researched.
- **Accessibility (711/TTY):**
  - 711 reaches TRS from any US phone.
  - The FCC says TTY users should call 911 directly in an emergency, not through 711.
  - 711 does not reach VRS, IP Relay or IP CTS.
  
  **[V]** ([FCC 711 guide PDF](https://Fcc.gov/sites/default/files/711_for_telecommunications_relay_service.pdf))
  - DIZA should accept relay-operator calls without timing out (Retell silence timeout) and tell deaf callers that LA County takes text-to-911. Whether Retell handles relay-call pacing is **[UNVERIFIED]**.

---

## (d) What to build in the hackathon, and what to say

### Top 10 features/integrations (hours, not weeks), in priority order

| # | Feature | Why (source) | Effort |
|---|---|---|---|
| 1 | **SMS location link.** The agent offers "I can text you a link that shares your exact location." A one-page web app calls `navigator.geolocation` and POSTs lat/lon (plus an optional photo) to the report. The dashboard pin is marked "GPS-verified" | Copies Carbyne c-Lite. Covers the AML-style location DIZA can't otherwise get. Needs a verified number or 10DLC, so in the demo, text to team phones | 3–4 h |
| 2 | **Location first, then verify by read-back.** Make cross streets/landmark the first intake slot and read it back | NENA §4.1.2 "ask and verify the location … first" | 1 h (prompt) |
| 3 | **Automatic abandoned-call callback.** Calls that drop under N seconds or end mid-intake get one automatic callback in the same modality. Skip it when the caller flagged danger (DV/hiding) or opted out, and log the attempt | NENA §5.4 / §5.4.1 | 2–3 h |
| 4 | **CAP 1.2 export of approved alerts.** "Download CAP XML" on each approved batch, with `<area>` set to a polygon or zone name. Refuse to approve an alert with no target area | IPAWS/NWS use CAP. Directly answers the 9 January 2025 lesson | 2 h |
| 5 | **NWS alert ingest.** Poll `api.weather.gov/alerts/active?area=CA` and show active LA alerts on the map. The agent can say "the National Weather Service has a red-flag warning for your area" | Live feed, verified working | 1–2 h |
| 6 | **Evacuation zone field + referral.** Add a `zone_id` (free text, e.g. `LOS-0767-D`) to reports and alerts. The agent says "look up your zone at protect.genasys.com or Alert LA County" | Genasys Protect is LA County's zone system. Zone format and API are unverified, so don't scrape | 1 h |
| 7 | **Open311 GeoReport v2 export.** `GET /open311/v2/requests.json` exposes non-emergency reports (service_code, lat/long, status, requested_datetime) | Real standard. This is the "a city can adopt us" story (no live MyLA311 API found) | 2 h |
| 8 | **HSDS-shaped resources.** Map `resources.yaml` to HSDS `organization/service/location/phone` and export JSON | 211s and resource directories use HSDS. Gives us a clean 211 LA handoff story | 1–2 h |
| 9 | **NENA metrics + surge banner on the dashboard.** Show % answered within 15 s / 20 s, abandoned %, callbacks queued, and "High Impact Event mode" (callback offers on, P2/P3 deferred) | NENA §4.1 benchmarks and §7 HIE. Shows we speak PSAP language | 2 h |
| 10 | **ICS-style situation summary.** One button generates a summary: incident, counts by priority, clusters, unmet needs, resources requested, as text/JSON for an EOC. Add an opt-in AFN flag (mobility, oxygen, language) on intake that feeds the welfare call-down list | NIMS COP. AFN registry practice (voluntary, confidential, no priority promise) | 2–3 h |

Also cheap and worth doing (under 30 minutes each):
- Add "If you can't speak, you can text 911 anywhere in LA County" to the crisis prompt and every SMS footer. ([LAFD](https://lafd.org/news/text-911-comes-los-angeles))
- Point non-USC callers to TrojansAlert by Nixle.
- Re-verify the 211 out-of-county number (800-339-6993 vs 800-708-6029).

### Five things to say in the pitch: DIZA complements 911, it doesn't replace it

1. **"NENA's 2026 call-processing standard asks for exactly this."** §5.6.2 encourages agencies to use AI to divert non-emergency calls, provided the system detects real emergencies and redirects them. DIZA does that: every P0 gets "hang up and call 911", and we never dispatch.
2. **"We take the 211/311 load off 911 during surges."** After the January 2025 fires, 211 LA logged 42,000+ contacts, and residents reported 911 busy signals. DIZA answers the "where's a shelter / my power's out / check on my mom" calls in four languages so 911 call-takers keep their lines for life safety.
3. **"We follow 911's own rules where they apply to us":**
   - Location first, read back (NENA §4.1.2).
   - One callback for every dropped call, in the same mode (§5.4.1).
   - Every duplicate report kept and evaluated, even when clustered (§5.5.6).
   - Translation for every caller (§5.5.5).
4. **"We speak the government's data standards, so nothing is a dead end":**
   - CAP 1.2 for alerts (the IPAWS format).
   - Open311 GeoReport v2 for city service requests.
   - HSDS for 211 resources.
   - A CSV/GeoJSON situation summary an EOC can drop into ArcGIS.
   
   A pilot with 211 LA or a council office would be an adapter, not a rewrite.
5. **"A human approves every alert, and every alert has a target."** WEA is EN/ES only and NotifyLA needs sign-up, so DIZA's voice batch calls reach Korean and Mandarin speakers and landline-only elders. After the 9 January 2025 countywide false alert, DIZA refuses to send any batch without supervisor approval and an explicit zone, and it always points people back to official sources (Alert LA County, NotifyLA, 911).

### Explicitly out of scope (say so if asked)
- PSAP functions: ALI, Phase II, RapidSOS data, CAD, ESInet/i3.
- Licensed EMD/EFD/EPD protocols.
- WEA/EAS/IPAWS origination (this requires a government alerting authority).
- Running an AFN registry.
- Live video.
- Dispatching any responder.

---

## Not verified / open items
- Current text of 47 CFR 64.1200 (eCFR blocked from the sandbox; quoted via law-firm summaries).
- Whether the FCC LBR 2026 deadlines were extended.
- The NotifyLA vendor.
- Whether Genasys Protect has a public API, and its exact zone ID format ("LAC-" not found).
- Whether Genasys ALERT supports two-way replies from residents.
- Whether MyLA311 has a public Open311 endpoint.
- Detailed 211 triage criteria (Inform USA standards text not read).
- Whether WEA languages were expanded beyond EN/ES.
- Whether Retell handles TRS/relay calls.
- California CMIA applicability.
- The Prepared/Axon acquisition date (secondary source only).
- Whether a non-PSAP could become a RapidSOS data partner.

> **Correction (2026-10-17, from research/WELFARE_CHECKS.md):** Alert LA County is not an AFN registry. LA County ended its SNAP disability registry around 2016; the outcome of a 2025 feasibility study is unverified. Treat the AFN-registry statements above as superseded.
