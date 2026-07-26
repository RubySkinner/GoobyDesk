Accessibility Audit — Key Findings
Global (styles.css)

No visible :focus style except inputs/selects/textareas. Buttons/links (.submit-btn, .status-btn, badges, a) have no :focus-visible outline → keyboard nav loses track. Add global focus ring.
input:focus sets outline: none with only a box-shadow replacement — fine, but same pattern isn't applied to buttons.
Badges (.badge-*) convey status by color only, no icon/text differentiator beyond label text (label text is present, so ok — just verify contrast).
.badge-warning #d29922 on rgba(210,153,34,.15) bg — check contrast ratio (borderline, likely under 4.5:1 for small text).
Layout / semantics

<center> tag used in error pages, new-ticket-email.html, under_construction.html — deprecated, not a semantic landmark. Low priority but consider <main>/div+CSS.
Multiple pages missing <main> landmark — body → div.container directly. Add role="main" or <main> wrapper for screen reader navigation.
No skip-to-content link anywhere.
500.html and others: error message not in a role="alert"/aria-live region — screen reader won't announce it automatically.
signup.html:33 has role="alert" on flash — good, but other pages (login.html, submit_new.html) show .alert--danger without role="alert". Inconsistent.
Forms

Password/text inputs generally have proper <label for> — good.
dashboard.html:18: <img src="static/img/logo_white.webp"> uses raw relative path instead of url_for, unrelated to a11y but inconsistent; alt text present though — fine.
Inline close-tkt-btn/status-btn buttons rely on onclick only — keyboard accessible since they're real <button> elements, good.
Tables

dashboard.html:25 table has <th> without scope="col". Same likely true in reports/changes/crm/hr dashboards — add scope="col" to all <th> for screen-reader table navigation.
Priority fixes (low risk, high value):

Add :focus-visible outline globally for links/buttons.
Add scope="col" to all <th> in dashboard tables.
Wrap flash/error alerts consistently with role="alert".
Add <main> landmark around primary content in each template.
Want me to implement these four fixes now?