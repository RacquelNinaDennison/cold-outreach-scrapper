# CSS selectors — verified against live site DOM (2026-03-28)
# Site uses custom HTML elements: <expert>, <opt>, <btn>, <pad>, <screen>, etc.

# Homepage
FIND_EXPERT_BTN = "#find-expert"

# Wizard step 1 — role selection
PT_OPTION = 'opt[data-value="personal-trainer"]'
NEXT_BTN = "btn.next"

# Wizard step 2 — club selection
CLUB_ITEM = "div.club-list > div[data-club]"

# Wizard steps 3-5 — goal/gender/budget (select "show all" to skip filtering)
SHOW_ALL_OPTION = 'opt[data-value="%na%"]'

# Listing page
EXPERT_CARD = "expert"

# Detail page
PROFILE_NAME = "h2.fullname"
CONTACTS_PAD = "pad.contacts"
SKILLS_PAD = "pad.skills"

# JS to extract all experts from the listing screen (no need to visit detail pages
# unless we want full contact info — the listing only has name/rate/image)
LISTING_EXTRACTION_JS = r"""
() => {
    const experts = document.querySelectorAll("expert");
    return Array.from(experts).map(e => ({
        trainer_id: e.id,
        name: e.getAttribute("data-name"),
        gender: e.getAttribute("data-gender"),
        rate: e.getAttribute("data-rate"),
        image_url: (() => {
            const div = e.querySelector("div.expert-img");
            if (!div) return null;
            const bg = div.style.backgroundImage;
            const match = bg.match(/url\(['"]?(.*?)['"]?\)/);
            return match ? match[1] : null;
        })(),
        role: e.querySelector("overline")?.innerText?.trim() ?? null,
    }));
}
"""

# JS to extract full profile details from a detail/contacts page
DETAIL_EXTRACTION_JS = r"""
() => {
    const pad = document.querySelector("screen.cur pad.contacts");
    if (!pad) return null;

    const locationEl = pad.querySelector(
        "icon.profile-icon-location"
    )?.closest("a")?.querySelector("p3") ??
    pad.querySelector("icon.profile-icon-location")?.nextElementSibling;
    const suburb = locationEl?.innerText?.trim() ?? null;

    const qualsEl = pad.querySelector(
        "icon.profile-icon-qualifications"
    )?.closest("a")?.querySelector("p3") ??
    pad.querySelector("icon.profile-icon-qualifications")?.nextElementSibling;
    const qualifications = qualsEl?.innerText?.trim() ?? null;

    const phoneLink = pad.querySelector("a[href^='tel:']");
    const phone = phoneLink
        ? phoneLink.getAttribute("href").replace("tel:", "")
        : null;

    const emailLink = pad.querySelector("a[href^='mailto:']");
    const email = emailLink
        ? emailLink.getAttribute("href").replace("mailto:", "")
        : null;

    const waLink = pad.querySelector("a[href*='wa.me/']");
    const waHref = waLink?.getAttribute("href") ?? null;
    const whatsapp_number = waHref
        ? waHref.replace(/https?:\/\/wa\.me\//, "").split("?")[0]
        : null;

    const igLink = pad.querySelector("a[href*='instagram.com']");
    const igUrl = igLink?.getAttribute("href") ?? null;
    const instagram_handle = igUrl
        ? igUrl.replace(/\/+$/, "").split("/").pop()
        : null;

    const fbLink = pad.querySelector("a[href*='facebook.com']");
    const facebook_url = fbLink?.getAttribute("href") ?? null;

    const webIcon = pad.querySelector("icon.profile-icon-web");
    const website = webIcon
        ? (webIcon.closest("a")?.getAttribute("href") ??
           webIcon.closest("a")?.querySelector("p3")?.innerText?.trim() ?? null)
        : null;

    // Profile image — CSS background-image on <imgvid>
    const imgvid = document.querySelector("screen.cur imgvid");
    let profile_image_url = null;
    if (imgvid) {
        const bg = imgvid.style.backgroundImage;
        const match = bg.match(/url\(['"]?(.*?)['"]?\)/);
        profile_image_url = match ? match[1] : null;
    }

    // Name
    const nameEl = document.querySelector("screen.cur h2.fullname");
    const name = nameEl?.innerText?.trim() ?? null;

    return {
        name, suburb, qualifications, phone, email, website,
        instagram_handle, facebook_url, whatsapp_number, profile_image_url
    };
}
"""
