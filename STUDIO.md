# Daily video playbook (for the scheduled run)

Goal: every day, make **one** new Reel for The Eye Centre (independent opticians, 56 High Street, Leicester,
est. 1974, theeyecentre.com) and post it to **Instagram and the Facebook Page**. Then tell the owner (Abbas) what went out.
`POSTS_PER_DAY = 1` (raise only if Abbas asks).

**Every video is brand new.** Never re-post or re-upload an existing video (the Black Friday reels "Stop Scrolling",
"Designer frames never go on sale" and the original Black Friday reel are running as paid Meta ads; the slot machine
video is retired). Abbas wants funny intros, viral/trending formats, animation and hooks that stop the scroll.

## 0. Setup (fresh session)
1. Attach this repo with push access (`add_repo yaseen177/eye-centre-reels`, access "push"), clone it with depth 1.
2. Check tools: `python3 -c "import PIL, numpy, cairosvg"` (if cairosvg is missing: `pip install --break-system-packages cairosvg`) and `ffmpeg -version`.
3. Read `history.json` — never reuse a product handle or the same hook wording used in the last 14 days; rotate the style
   (gold → punch → cream → gold …) and the format (offer / versus / feature / list / brand spotlight / new in / price-point).

## 1. Facts to check in Shopify every day (Shopify connector, graphql_query)
- **Live offers.** `discountNodes(query: "status:active")`. Only mention an offer that is ACTIVE now and still active at
  posting time. Black Friday 2026 = automatic discount "Black Friday 30% off frames" (frames in the "black-friday-sale"
  collection; excludes Ray-Ban Meta; ends 2026-12-01T23:59:59Z). EYE20 = code, 20% off frames online. If no offer is
  live, make a non-offer video (features, brands, new in, versus, eye tests). Never invent an offer or a deadline.
  During the Black Friday sale: no specific dates on screen ("ends soon" / "last day" only when true).
- **Products.** Pick 1–4 that are `status:ACTIVE`, available, with a featured image. Vary brands. Read the price from
  `priceRangeV2.minVariantPrice` today. Sale price = price × (1 − discount), rounded to the penny, only for products
  the discount actually covers. Show "From" thinking: if variants differ in price, use the lowest and don't show a "was" price.
- The live theme id: `themes(first: 1, roles: [MAIN]) { nodes { id } }`.

## 2. Product photos
1. `theme_screenshot` of `/products/<handle>` on the live theme, viewport `desktop`. The tool output names the saved
   file ("Image: source: /tmp/...webp").
2. `python3 -I studio/cut.py <that file> studio/assets/cutouts/<handle>.png`
3. Look at the cut-out (Read the PNG). Reject it and pick another product if the frame is cropped, has page UI in it,
   or the background is not clean. Reuse cut-outs already in `studio/assets/cutouts/` when the handle matches.

## 2b. Real shop photos (Abbas asked for these — "to give people the feel that we are real")
- Cleaned photos of the shop are in `studio/assets/store/` (storefront, shop-floor, brand-wall, rayban-wall);
  `studio/assets/store/photos.json` says what each shows and how to frame it. Use **only** these files — never the
  originals (they contain a model poster, ad cards with people, passers-by, a Mulberry card and % stickers).
- Use them in **roughly every second or third reel** (not every one), as 1–2 `shop` scenes (see `studio/store.py`,
  example `studio/examples/shop-photos.json`): `pan` = full-screen slow pan/zoom over an interior shot, `print` = the
  storefront as a photo print dropping in. Don't use the same photo two reels running (check `shop_photos` in history).
- Good spots: right after the hook ("THIS IS US", "COME SAY HI", "WALLS OF DESIGNER FRAMES", "RAY-BAN CORNER"),
  or just before the end card with the storefront print captioned "56 High Street, Leicester".
- The interior photos show in-store **SALE** signs. Use the normal framing only while a Shopify offer is live; when no
  offer is live use the storefront, or the `no_offer_safe` framing in photos.json (checked: no SALE sign in shot).
- Words on shop scenes follow the same rules: nothing unverified (no opening hours, stock claims, "biggest", etc.).
  Brands may be named only if they are in the online brand list below.
- Prefer the gold or punch style for `pan` (white text on a darkened photo); `print` works in every style.

## 3. Build the video
1. Write `studio/specs/<date>-<slug>.json` (format documented at the top of `studio/engine.py` and `studio/viral.py`;
   see `studio/examples/`, especially `funny-chat.json`; example prices are NOT current — always re-read prices). 10–16 seconds total, 4–6 scenes, always ending with an `end`
   scene. Logo is automatic on every scene.
2. **The first scene is the hook and should be funny or viral-style** — it must make people stop in the first second.
   Use one of the viral scene types as the opener (write NEW wording every day, these are only examples):
   - `chat` (fake text conversation — funniest, best performer). Contacts are generic: Mum, Dad, Bestie, Boss, My Bank,
     My Wallet, The Group Chat, Me in 2019. e.g. Me: "Mum I need new glasses" / Mum: "We have glasses at home" /
     Me: "They're Gucci" / Mum: "Send me the link". Or My Bank: "Please stop buying designer things" / Me: "They're
     30% off" / My Bank: "…carry on".
   - `pov` caption over a product: "POV: you finally found frames that actually suit your face",
     "POV: your optometrist says you need glasses and you're secretly happy", "POV: your new Tom Fords just arrived".
   - `glitch`: "WAIT." / "DON'T BUY" / "GLASSES YET"; "ERROR:" / "TOO MANY" / "NICE FRAMES".
   - `search`: someone typing "designer glasses leicester" or "where to buy gucci glasses" → The Eye Centre appears.
   - `rate` ("Rating frames 1–10", "Rating Leicester's best frames", stamp "11/10") or `guess` ("Guess the price",
     reveal with confetti) as the opener or the middle.
   - Classic `hook` lines still work: "STOP SCROLLING", "Which would you pick?".
   Then 2–4 scenes showing real products/features, then `end`.
   Humour rules: punch up at situations (wallets, choosing frames, squinting at menus), never at customers, people's
   looks, age, eyesight problems or any condition. No real people or celebrities, no film/TV characters or quotes,
   no copyrighted music or trending sounds (the engine makes its own soundtrack), no swearing, no competitor names.
   Scores like "10/10" are our playful opinion of a frame, never presented as customer reviews.
3. Contact sheet first: `python3 -I studio/engine.py <spec> /tmp/sheet.png --frames` → Read it → fix any text that
   overlaps, runs off screen or is too small. Then render:
   `python3 -I studio/engine.py <spec> videos/<date>-<slug>.mp4`

## 4. Website features you may use (approved wording)
| Feature | Say | Never say |
|---|---|---|
| Home trial | "Try up to 2 frames at home for 10 days" | "free" home trial, or its price |
| Virtual try-on | "Try frames on virtually before you order" | |
| Frame finder chat | "Not sure? Ask our frame finder on the website" | |
| Lenses | "Prescription lenses by Essilor" | "glazed in-house" |
| Varifocals | "Order varifocals online with two photos" | |
| Checks | "Every prescription checked by our optometrist" | |
| Pay later | "Pay later with Klarna or Clearpay" | |
| Delivery | "UK delivery" | delivery times you haven't checked |
| Eye tests | "Book an eye test in Leicester — book.theeyecentre.com", "NHS eye tests if you're eligible" | any eye-health condition or medical claim |
| Practice | "Independent opticians since 1974", "56 High Street, Leicester" | |
Brands online: Gucci, Saint Laurent, Tom Ford, Ray-Ban (vendor stored as "RayBan"), Oakley, Burberry,
Polo Ralph Lauren, Armani Exchange, Ray-Ban Meta. **Prada and Mulberry are not sold online** — never in online content.
Never: OCT scans, made-up reviews or numbers, re-posting old videos, competitor names, countdown "timers", gambling imagery (slot machines,
jackpots, spinning reels), anything about patients.

## 5. Publish
1. Commit the video + spec, push to `main`. The public link is
   `https://yaseen177.github.io/eye-centre-reels/videos/<file>.mp4` — wait ~90 s for GitHub Pages, then WebFetch the
   site root to confirm it is up.
2. Caption: hook line, 1–2 short sentences, "Shop at theeyecentre.com" (or "Book at book.theeyecentre.com"),
   any small print the offer needs (e.g. "Frames only. Excludes Ray-Ban Meta."), then **at most 5 hashtags**
   (Instagram's hard limit), e.g. #designerglasses #eyewear #leicester #opticians + one topical.
3. Windsor.ai `execute_action`:
   - Instagram: connector `instagram`, account `17841407499244499`, action `create_video_post`,
     params `{video_url, caption, share_to_feed: true, thumb_offset: <ms of the best frame>}`
   - Facebook: connector `facebook_organic`, account `1330737563467275`, action `create_reel`,
     params `{video_url, description: caption}`
   If Meta can't fetch the video yet, wait 2 minutes and retry once.
4. Append to `history.json`: date, file, style, format, hook, product handles, offer, `shop_photos` (list of
   store photo files used, or []), IG/FB result. Commit + push.
5. Message Abbas: what was posted, the hook, the products, and the links (or the exact error).

## Hard rules
- Organic posts only. Never create or change ads, budgets, discounts, products or the theme.
- If anything in sections 1–4 can't be verified, leave it out rather than guess.
- If the run can't produce a good video, post nothing and tell Abbas why.
- Delete videos older than 60 days from `videos/` (they are already posted) to keep the repo small.
