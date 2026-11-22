/* Rugby League BC: "Ask RLBC" help chat.
   Answers come only from what is published on this website. No AI service, nothing is stored or sent.
   Anything it cannot answer goes to the board through the contact form.
   Club names, dates, registration status and links are filled in at build time from the site data (data/*.json),
   so edits made in the CMS flow through. To change wording, edit the TOPICS list below. */
(function () {
  'use strict';
  var d = document;
  var DATA = /*RLBC_DATA*/ null;
  if (!DATA) return;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var BOARD = 'board@rugbyleaguebc.ca';

  function a(href, txt, ext) { return '<a href="' + href + '"' + (ext ? ' target="_blank" rel="noopener"' : '') + '>' + txt + '</a>'; }
  function mail(addr) { return a('mailto:' + addr, addr); }
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function fdate(s) { var p = (s || '').split('-'); return p.length === 3 ? MON[+p[1] - 1] + ' ' + (+p[2]) : s; }
  function list(arr) { return arr.length < 2 ? arr.join('') : arr.slice(0, -1).join(', ') + ' and ' + arr[arr.length - 1]; }

  var clubs = DATA.clubs || [];
  var competing = clubs.filter(function (c) { return !c.status; }).map(function (c) { return c.name; });
  var todayIso = new Date().toISOString().slice(0, 10);
  var upcoming = (DATA.events || []).filter(function (e) { return (e.end_date || e.date) >= todayIso; });

  function seasonLine() {
    var p = DATA.provisional || [];
    if (!p.length) return 'The 2027 draw is still being finalised. It goes up on the fixtures page as soon as it is confirmed.';
    var pick = function (re) { for (var i = 0; i < p.length; i++) if (re.test(p[i].label)) return p[i]; };
    var n = pick(/9s/i), r1 = pick(/Round 1/i), gf = pick(/Grand final/i);
    var bits = [];
    if (n) bits.push('the RLBC 9s on ' + fdate(n.date));
    if (r1) bits.push('Round 1 on ' + fdate(r1.date));
    if (gf) bits.push('the Grand Final on ' + fdate(gf.date));
    return 'The 2027 draw is still being finalised, so dates are provisional. Current plan: ' + list(bits) + '. The season is a round-robin followed by semi-finals and a Grand Final.';
  }

  var regLinks = DATA.registration_open
    ? [['Register to play', '/get-involved/#play']]
    : [['Registration details', '/get-involved/#play'], ['Join the mailing list', DATA.mailing_list_url, 1]];

  /* Each topic: words that trigger it, the answer, and follow-up buttons [label, link, external?]. */
  var TOPICS = [
    { id: 'play', label: 'How do I play?',
      keys: ['play', 'join', 'sign up', 'signup', 'register', 'registration', 'new player', 'try', 'trial', 'tryout', 'beginner', 'never played', 'want to play', 'teamsnap', 'one day', 'how do i'],
      a: DATA.registration_open
        ? 'Welcome. Registration runs through TeamSnap, with separate forms for men, women, masters, one-day players and admin. New to the game? The one-day form is for players who have never played rugby league. Clubs train in the Lower Mainland and Whistler, so find the one nearest you.'
        : 'Welcome. Registration for the 2027 season is not open yet. The TeamSnap links go up on the Get involved page as soon as it opens. Meanwhile, find the club nearest you and get in touch, or join the mailing list so you hear first.',
      go: regLinks.concat([['Find a club', '/clubs/']]) },
    { id: 'newplayer', label: 'I have never played',
      keys: ['never', 'new to', 'first time', 'complete beginner', 'no experience', 'inexperienced', 'try rugby league', 'learn'],
      a: 'No experience needed. RLBC runs "Try Rugby League" events, often with Canada Rugby League, and the one-day registration is for people who have never played. Rugby league is 13 a side, with a six-tackle rule, and the Rugby league explained page walks through it.',
      go: [['Rugby league explained', '/rugby-league-explained/'], ['Get involved', '/get-involved/#play']] },
    { id: 'union', label: 'I play rugby union',
      keys: ['union', 'rugby union', '15s', 'difference', 'different', 'rules', 'six tackle', 'tackle', 'transition', 'positions', 'what is rugby league', 'what is league'],
      a: 'Union players are welcome. League is 13 a side, with a six-tackle limit and a play-the-ball after each tackle. The site has a video on the rules, a union versus league comparison, and a coaches guide to moving players from union to league.',
      go: [['Rugby league explained', '/rugby-league-explained/'], ['Coaching the transition (PDF)', '/assets/docs/rlbc-coaching-transition-union-to-league.pdf', 1]] },
    { id: 'clubs', label: 'Which clubs are there?',
      keys: ['club', 'clubs', 'team', 'teams', 'near me', 'nearest', 'where can i play', 'whistler', 'wolves', 'thunder', 'point grey', 'ubc', 'dragons', 'vancouver dragons', 'vipers', 'langley', 'warriors', 'cougars', 'squamish', 'surrey', 'abbotsford', 'kelowna', 'richmond', 'who plays'],
      a: competing.length ? ('The clubs currently competing are ' + list(competing) + '. They are based in the Lower Mainland and Whistler. Each club page has home field, coaches and contact details. Want to start a club in your area? Email ' + mail(BOARD) + '.') : ('Club details are on the Clubs page. Want to start a club in your area? Email ' + mail(BOARD) + '.'),
      go: [['Find a club', '/clubs/'], ['Start a team', '/contact/?topic=Starting%20a%20club']] },
    { id: 'season', label: 'When is the season?',
      keys: ['season', 'schedule', 'fixture', 'fixtures', 'draw', 'when', 'dates', 'date', 'calendar', 'round', 'rounds', 'semi', 'final', 'finals', 'grand final', 'game day', 'match', 'matches', 'kick off', 'kickoff', 'results', 'ladder', 'table', 'standings'],
      a: seasonLine() + ' Results and the ladder are on the fixtures page.',
      go: [['Fixtures and results', '/fixtures/']] },
    { id: 'nines', label: 'RLBC 9s tournament',
      keys: ['9s', 'nines', "9's", 'tournament', 'pre-season', 'preseason', 'high school', 'high school nines'],
      a: 'The RLBC 9s is the annual pre-season tournament, with men\'s and women\'s divisions, usually run as a single day. Clubs get on the field and new players get an easy introduction to the game. The 2027 date is provisional (see the fixtures page), and the event is looking for a title sponsor. There is also a High School 9s program for younger players.',
      go: [['Competitions', '/competitions/#nines'], ['Fixtures', '/fixtures/'], ['Sponsor the 9s', '/partners/']] },
    { id: 'women', label: 'Women\'s rugby league',
      keys: ['women', "women's", 'womens', 'woman', 'female', 'girls', 'ladies', 'storm', 'bc storm'],
      a: 'Yes, women play. The women\'s competition runs several 9s tournaments through June, then a three-round 13-a-side competition in July. BC Storm is the women\'s provincial team. Follow them on Instagram at ' + a('https://www.instagram.com/rlbcstorm/', '@rlbcstorm', 1) + '.',
      go: [['Women\'s competition', '/competitions/#womens'], ['BC Storm', '/representative-teams/#storm']] },
    { id: 'masters', label: 'Masters (35 and over)',
      keys: ['masters', 'master', 'over 35', '35', 'older', 'silver foxes', 'veterans', 'vets', 'age'],
      a: 'Masters rugby league is for players 35 and over, and it is all about staying in the game and having fun. The BC Silver Foxes are the masters team, and RLBC is pulling together a squad for a game or two. Email ' + mail('masters@rugbyleaguebc.ca') + ' to put your name down.',
      go: [['BC Silver Foxes', '/representative-teams/#silver-foxes']] },
    { id: 'rep', label: 'Representative teams',
      keys: ['rep', 'representative', 'bulldogs', 'bc bulldogs', 'provincial', 'alberta', 'interprovincial', 'canada west', 'selection', 'select', 'national', 'canada', 'team bc', 'wedgetails', 'wellington'],
      a: 'RLBC picks representative teams each year: BC Bulldogs (men), BC Storm (women) and BC Silver Foxes (masters). They play an interprovincial series against Alberta over the September long weekend, and it is a pathway to Canada West and national selection. Selection criteria for the coming season are still to be set.' + (upcoming.length ? ' Next up: ' + upcoming[0].title + ' on ' + fdate(upcoming[0].date) + '.' : ''),
      go: [['Representative teams', '/representative-teams/']] },
    { id: 'coach', label: 'Coaching',
      keys: ['coach', 'coaching', 'nccp', 'certification', 'certified', 'criminal record', 'crc', 'manual', 'coaches'],
      a: 'RLBC coaches work at every level. Current requirements are the NCCP modules (Coach Initiation in Sport, Making Ethical Decisions, Emergency Action Plan, Making Headway in Sport), plus a Criminal Record Check for anyone working with youth. The site has the match coaches manual and a guide to coaching the move from union to league. For anything else, contact Director of Rugby Stephen Lenahan at ' + mail('Stephen.Lenahan@rugbyleaguebc.ca') + '.',
      go: [['Coaching on Get involved', '/get-involved/#coach'], ['Match coaches manual (PDF)', '/assets/docs/rlbc-match-coaches-manual.pdf', 1]] },
    { id: 'ref', label: 'Refereeing',
      keys: ['referee', 'referees', 'ref', 'refs', 'refereeing', 'officiate', 'officiating', 'official', 'officials', 'umpire', 'whistle'],
      a: 'RLBC is always looking for new officials. To get started as an official, email Blake Stewart at ' + mail('blake.stewart@rugbyleaguebc.ca') + '.',
      go: [['Officiating on Get involved', '/get-involved/#officiate']] },
    { id: 'vol', label: 'Volunteering',
      keys: ['volunteer', 'volunteering', 'volunteers', 'help out', 'help', 'committee', 'non player', 'not playing', 'board member', 'join the board'],
      a: 'Volunteers keep the league running, through committees and at events. Fill in the volunteer form and the board will be in touch. Several board roles are also open, including Secretary, VP Partnerships and VP Communications.',
      go: [['Volunteer form', DATA.volunteer_form_url, 1], ['Board and roles', '/about/#board']] },
    { id: 'support', label: 'Supporters club',
      keys: ['supporter', 'supporters', 'fan', 'fans', 'watch', 'spectator', 'spectate', 'support', 'follow'],
      a: 'You do not have to play to be part of it. The supporters club has a signup form, and the mailing list and social channels (Instagram, Facebook, YouTube) cover news and match days.',
      go: [['Join the supporters club', DATA.supporters_signup_url, 1], ['Join the mailing list', DATA.mailing_list_url, 1]] },
    { id: 'spon', label: 'Sponsorship',
      keys: ['sponsor', 'sponsors', 'sponsorship', 'sponsoring', 'advertise', 'advertising', 'partner', 'partners', 'partnership', 'logo', 'package', 'business', 'company', 'donate', 'donation'],
      a: 'RLBC offers flexible sponsorship packages for businesses and individuals, and the RLBC 9s is looking for a title sponsor. The 2027 sponsorship package sets out the options. Contact Richard Marshall at ' + mail('richard.marshall@rugbyleaguebc.ca') + '.',
      go: [['Partners and sponsorship', '/partners/'], ['2027 sponsorship package (PDF)', '/assets/docs/rlbc-sponsorship-2027.pdf', 1]] },
    { id: 'work', label: 'New to BC, need work',
      keys: ['work', 'job', 'jobs', 'employment', 'moving', 'newcomer', 'overseas', 'international', 'immigrant', 'visa', 'abroad', 'relocate', 'relocating', 'new to bc', 'new to vancouver', 'accommodation'],
      a: 'New to BC or coming from overseas? Community contacts at A&B Tool Rentals and Madden Solutions may be able to connect you with work, including general labour, construction and moving. Details are on the Partners page.',
      go: [['Work and community contacts', '/partners/'], ['Message the board', '/contact/?topic=playing']] },
    { id: 'store', label: 'Merch and store',
      keys: ['merch', 'merchandise', 'shop', 'store', 'jersey', 'jerseys', 'hoodie', 'shirt', 'gear', 'buy', 'order'],
      a: 'RLBC merchandise is sold through the official online store.',
      go: [['Open the store', DATA.store_url, 1]] },
    { id: 'about', label: 'About RLBC',
      keys: ['about', 'what is rlbc', 'rlbc', 'who are you', 'history', 'founded', 'started', 'governance', 'bylaws', 'constitution', 'rulebook', 'strategic plan', 'non profit', 'nonprofit', 'mandate', 'vision', 'mission', 'board', 'president', 'premiers', 'premier', 'champions', 'won', 'winner'],
      a: 'Rugby League British Columbia is the non-profit governing body for rugby league in BC, founded in 2011 and operating under Canada Rugby League. It runs the largest domestic rugby league competition in Canada. ' + (DATA.premier ? DATA.premier : '') + 'The About page has the vision, history, past premiers, board and governing documents (rules, bylaws, strategic plan).',
      go: [['About RLBC', '/about/'], ['Past premiers', '/about/#honour-roll']] },
    { id: 'cost', label: 'What does it cost?',
      keys: ['cost', 'costs', 'fee', 'fees', 'price', 'how much', 'pay', 'paid', 'insurance', 'free', 'membership', 'dues'],
      a: 'Fees for 2027 have not been published yet. They will be shown with the registration forms on the Get involved page once registration opens. For a specific club, contact them directly.',
      go: [['Get involved', '/get-involved/#play'], ['Club contacts', '/clubs/']] },
    { id: 'contact', label: 'Contact the board',
      keys: ['contact', 'email', 'e-mail', 'phone', 'call', 'reach', 'instagram', 'facebook', 'youtube', 'message', 'talk to', 'speak to', 'human', 'person', 'media', 'press', 'question'],
      a: 'Email the board at ' + mail(BOARD) + ', or use the contact form and pick the topic so it reaches the right person. You can also message @rugbyleaguebc on Instagram.',
      go: [['Contact form', '/contact/'], ['Instagram', DATA.instagram_url, 1]] },
    { id: 'hi', keys: ['hi', 'hello', 'hey', 'gday', "g'day", 'yo', 'morning', 'evening'],
      a: 'Hi. What would you like to know? Pick a topic below or type a question.', go: [] },
    { id: 'thanks', keys: ['thanks', 'thank you', 'cheers', 'ta', 'great', 'awesome'],
      a: 'Happy to help. Ask anything else any time.', go: [] }
  ];
  var MENU = ['play', 'clubs', 'season', 'coach', 'spon', 'contact'];
  var FALLBACK = 'I do not have an answer for that on the website. Send it to the board and someone will reply by email.';

  function norm(t) { return ' ' + t.toLowerCase().replace(/[’]/g, "'").replace(/[^a-z0-9'\s-]/g, ' ').replace(/\s+/g, ' ').trim() + ' '; }
  function match(q) {
    var t = norm(q), best = null, score = 0;
    TOPICS.forEach(function (tp) {
      var s = 0;
      tp.keys.forEach(function (k) { if (t.indexOf(' ' + k + ' ') > -1 || (k.length > 4 && t.indexOf(k) > -1)) s += k.indexOf(' ') > -1 ? 2 : 1; });
      if (s > score) { score = s; best = tp; }
    });
    return best;
  }
  function byId(id) { for (var i = 0; i < TOPICS.length; i++) if (TOPICS[i].id === id) return TOPICS[i]; }

  /* Build the widget */
  var root = d.createElement('div'); root.className = 'rchat';
  root.innerHTML =
    '<button class="rchat-launch" type="button" aria-expanded="false" aria-controls="rchatPanel">' +
      '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="currentColor" d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 4v-4H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm3 6.5a1.5 1.5 0 1 0 0 .01zm5 0a1.5 1.5 0 1 0 0 .01zm5 0a1.5 1.5 0 1 0 0 .01z"/></svg>' +
      '<span>Questions?</span></button>' +
    '<div class="rchat-panel" id="rchatPanel" role="dialog" aria-label="Ask RLBC" hidden>' +
      '<div class="rchat-head"><img src="/assets/img/crest-160.webp" alt="" width="28" height="28"><div><b>Ask RLBC</b><small>Quick answers from this site</small></div>' +
      '<button class="rchat-x" type="button" aria-label="Close chat"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M6.4 5 5 6.4 10.6 12 5 17.6 6.4 19l5.6-5.6 5.6 5.6 1.4-1.4-5.6-5.6L19 6.4 17.6 5 12 10.6z"/></svg></button></div>' +
      '<div class="rchat-log" role="log" aria-live="polite"></div>' +
      '<form class="rchat-in" autocomplete="off"><label class="vh" for="rchatQ">Type your question</label>' +
      '<input id="rchatQ" type="text" placeholder="Ask about playing, clubs, the season…" maxlength="200">' +
      '<button type="submit" aria-label="Send"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M3 20.5 21 12 3 3.5v6.6l12 1.9-12 1.9z"/></svg></button></form>' +
    '</div>';
  d.body.appendChild(root);
  var btn = root.querySelector('.rchat-launch'), panel = root.querySelector('.rchat-panel'), log = root.querySelector('.rchat-log'),
      form = root.querySelector('.rchat-in'), input = root.querySelector('#rchatQ'), started = false;

  function scroll() { log.scrollTop = log.scrollHeight; }
  function say(html, who) { var m = d.createElement('div'); m.className = 'rchat-msg ' + (who || 'bot'); if (who === 'me') m.textContent = html; else m.innerHTML = html; log.appendChild(m); scroll(); return m; }
  function chips(items) {
    if (!items.length) return;
    var w = d.createElement('div'); w.className = 'rchat-chips';
    items.forEach(function (c) {
      var el;
      if (typeof c === 'string') { var tp = byId(c); el = d.createElement('button'); el.type = 'button'; el.textContent = tp.label; el.addEventListener('click', function () { ask(tp.label, tp); }); }
      else { el = d.createElement('a'); el.href = c[1]; el.textContent = c[0] + (c[2] ? ' ↗' : ' →'); if (c[2]) { el.target = '_blank'; el.rel = 'noopener'; } }
      w.appendChild(el);
    });
    log.appendChild(w); scroll();
  }
  function reply(tp) {
    var go = function () {
      if (tp) { say(tp.a); chips(tp.go.concat(tp.id === 'hi' ? MENU : [])); }
      else { say(FALLBACK); chips([['Message the board', '/contact/'], 'play', 'clubs', 'season']); }
    };
    if (reduce) return go();
    var t = say('<span class="dots" aria-label="Typing"><i></i><i></i><i></i></span>'); t.classList.add('typing');
    setTimeout(function () { t.remove(); go(); }, 420);
  }
  function ask(text, tp) { say(text, 'me'); reply(tp || match(text)); }
  function start() {
    if (started) return; started = true;
    say('Hi. I can answer common questions about playing, clubs, the season, coaching, volunteering and sponsorship. For anything else, I will point you to the board.');
    chips(MENU);
  }
  function open() { panel.hidden = false; btn.setAttribute('aria-expanded', 'true'); root.classList.add('open'); start(); setTimeout(function () { input.focus(); }, 30); }
  function close() { panel.hidden = true; btn.setAttribute('aria-expanded', 'false'); root.classList.remove('open'); btn.focus(); }
  btn.addEventListener('click', function () { panel.hidden ? open() : close(); });
  root.querySelector('.rchat-x').addEventListener('click', close);
  d.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) close(); });
  form.addEventListener('submit', function (e) { e.preventDefault(); var q = input.value.trim(); if (!q) return; input.value = ''; ask(q); });
})();
