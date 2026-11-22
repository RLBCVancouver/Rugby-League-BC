# Rugby League BC website

Planned live address: https://www.rugbyleaguebc.ca (currently a draft preview)

## For RLBC: how to edit the site

1. Go to **https://app.pagescms.org** and sign in with GitHub.
2. Open the RLBC site.
3. Pick what you want to change on the left:
   - **Fixtures, results and events**: add matches, enter scores, list upcoming events. The ladder works itself out from the scores.
   - **News**: add or edit articles. The first three show on the home page.
   - **Clubs**: contacts, coaches, home fields and crests. Each club gets its own page.
   - **Past premiers**: one line per season. Club honours are counted from this list.
   - **Board**, **Partners**, **Site settings and links** (registration links, social media, mailing list).
4. Click **Save**. The website updates by itself in about a minute.

Tips
- Enter a match first with no score. Add the score after the game and the ladder updates.
- Only rounds named "Round 1", "Round 2" and so on count towards the ladder. Semi-finals and the grand final do not.
- Team names can be typed short ("Wolves") or in full ("Whistler Wolves").
- Events hide themselves once their date has passed.
- When the 2027 draw is confirmed: enter the matches, then turn off the yellow notice and the provisional dates block.
- If something won't save, or the site doesn't update, check the Deploys page in Netlify. A mistake in the content stops the update and leaves the previous version live, with a message saying what to fix.

### Optional: run fixtures from a Google Sheet

The site can read fixtures and scores straight from a Google Sheet each time someone opens the Fixtures page.

1. Import `fixtures-sheet-template.csv` into a new Google Sheet. Keep the header row exactly as it is: `date, round, home, away, home_score, away_score, venue, time, note`. Dates are written `2027-05-29`.
2. File > Share > Publish to web > choose the sheet tab > **Comma-separated values (.csv)** > Publish. Copy the link.
3. In Pages CMS, open **Site settings and links** and paste the link into **Live fixtures Google Sheet**.

Anyone can read a published sheet, so keep private details out of it. If the sheet can't be read, the page shows the matches saved in Pages CMS instead. The home page and club pages always use the matches saved in Pages CMS.

## At launch

- In Pages CMS > Site settings, turn off **Hide the site from Google and other search engines**.
- In `_headers`, delete the `X-Robots-Tag: noindex, nofollow` line.
- Point the domain at Netlify and set it as the primary domain. Page addresses, the sitemap and link previews pick up the domain on the next deploy.
- In Netlify > Forms, set the notification email for the `rlbc-contact` form.
- `_redirects` already sends every old Google Sites address to its new page.

## For developers

- `pages/*.html` hold each page's text. Lines above `---` are the page's address, title and description. `{{name}}` markers are filled in by `build.py`.
- `data/*.json` hold the editable content. `.pages.yml` defines the editing screens.
- `build.py` (Python 3.8+, no packages needed) writes the finished site to `dist/`, including one page per club and per news article, `sitemap.xml`, `robots.txt` and `llms.txt`.
- `netlify.toml` sets the build command and publish folder. Run locally: `python3 build.py`, then serve `dist/`.
- Site built and maintained by McLeod Technologies Corp., Official Technology Partner.
