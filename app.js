document.addEventListener("DOMContentLoaded", () => {

    const API_URL = "http://127.0.0.1:8000";

    const searchInput = document.getElementById("search");
    const searchButton = document.querySelector(".search-box .button");
    const marketSelect = document.getElementById("market");
    const categories = document.querySelectorAll(".category");
    const offersGrid = document.querySelector(".offers-grid");

    let selectedCategory = "all";
    let currentSearch = "";
    let offers = [];
    let requestVersion = 0;

    // ======================================
    // MARKET
    // ======================================

    function getMarket() {
        return marketSelect ? marketSelect.value : "US";
    }

    // ======================================
    // CATEGORY
    // ======================================

    function normalizeCategory(name) {

        const value = name.toLowerCase();

        if (value.includes("electronic")) return "Electronics";
        if (value.includes("gaming")) return "Gaming";
        if (value.includes("supplement")) return "Supplements";
        if (value.includes("beauty")) return "Beauty";
        if (value.includes("pet")) return "Pets";
        if (value.includes("home")) return "Home";
        if (value.includes("fashion")) return "Fashion";
        if (value.includes("deal")) return "all";

        return name;
    }

    // ======================================
    // PRODUCT ICONS
    // ======================================

    function getProductIcon(product) {

        const value = (
            (product.name || "") + " " +
            (product.category || "")
        ).toLowerCase();

        if (value.includes("headphone")) return "🎧";
        if (value.includes("keyboard")) return "⌨️";
        if (value.includes("watch")) return "⌚";
        if (value.includes("gaming")) return "🎮";

        return "📦";
    }

    // ======================================
    // SYSTEM MESSAGES
    // ======================================

    function showMessage(title, description, icon = "🔎") {

        if (!offersGrid) return;

        offersGrid.replaceChildren();

        const container = document.createElement("div");
        container.className = "empty-state";

        const iconElement = document.createElement("div");
        iconElement.className = "icon";
        iconElement.textContent = icon;

        const heading = document.createElement("h3");
        heading.textContent = title;

        const paragraph = document.createElement("p");
        paragraph.textContent = description;

        container.append(iconElement, heading, paragraph);
        offersGrid.appendChild(container);
    }

    // ======================================
    // API REQUEST HELPER
    // ======================================

    async function fetchJSON(url) {

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return response.json();
    }

    // ======================================
    // OFFER HISTORY
    // ======================================

    async function getOfferHistory(offerId) {

        try {

            const history = await fetchJSON(
                `${API_URL}/offers/${offerId}/history`
            );

            if (!Array.isArray(history) || history.length === 0) {
                return null;
            }

            return history[history.length - 1];

        } catch (error) {

            console.error("History error:", offerId, error);
            return null;
        }
    }

    // ======================================
    // OFFER ANALYSIS
    // ======================================

    async function getOfferAnalysis(offerId) {

        try {

            return await fetchJSON(
                `${API_URL}/offers/${offerId}/analysis`
            );

        } catch (error) {

            console.error("Analysis error:", offerId, error);
            return null;
        }
    }

    // ======================================
    // PRODUCT COMPARISON
    // ======================================

    async function getProductComparison(productCode) {

        try {

            return await fetchJSON(
                `${API_URL}/products/${encodeURIComponent(productCode)}/comparison`
            );

        } catch (error) {

            console.error("Comparison error:", productCode, error);
            return null;
        }
    }

    // ======================================
    // LOAD OFFERS
    // ======================================

    async function loadOffers() {

        if (!offersGrid) return;

        const version = ++requestVersion;
        const market = getMarket();

        showMessage(
            "Loading offers...",
            "Connecting to the Webeout database.",
            "⏳"
        );

        try {

            const data = await fetchJSON(
                `${API_URL}/offers?market=${encodeURIComponent(market)}`
            );

            if (version !== requestVersion) return;

            if (!Array.isArray(data)) {
                throw new Error("Invalid offers response.");
            }

            const activeOffers = data.filter(offer =>
                Number(offer.is_active) === 1 &&
                offer.market === market
            );

            // Load each offer's own history and analysis.

            const enrichedOffers = await Promise.all(

                activeOffers.map(async offer => {

                    const [latestPrice, analysis] = await Promise.all([
                        getOfferHistory(offer.id),
                        getOfferAnalysis(offer.id)
                    ]);

                    return {
                        ...offer,
                        latestPrice,
                        analysis
                    };
                })
            );

            if (version !== requestVersion) return;

            // Compare each distinct product only once.

            const productCodes = [
                ...new Set(
                    enrichedOffers.map(offer => offer.product_code)
                )
            ];

            const comparisons = await Promise.all(

                productCodes.map(async code => ({
                    code,
                    result: await getProductComparison(code)
                }))
            );

            const comparisonMap = new Map(
                comparisons.map(item => [item.code, item.result])
            );

            enrichedOffers.forEach(offer => {

                offer.comparison = comparisonMap.get(
                    offer.product_code
                );

                offer.isBestOffer =
                    Number(offer.comparison?.best_offer?.offer_id) ===
                    Number(offer.id);
            });

            if (version !== requestVersion) return;

            offers = enrichedOffers;

            renderOffers();

        } catch (error) {

            console.error("Webeout API error:", error);

            if (version !== requestVersion) return;

            showMessage(
                "Connection unavailable",
                "The Webeout API could not be reached. Make sure the Python server is running.",
                "⚠️"
            );
        }
    }

    // ======================================
    // FORMAT PRICE
    // ======================================

    function formatMoney(value, currency, market) {

        if (value === null || value === undefined ||
            !Number.isFinite(Number(value))) {
            return "Unavailable";
        }

        return new Intl.NumberFormat(
            market === "DE" ? "de-DE" : "en-US",
            {
                style: "currency",
                currency: currency || "USD"
            }
        ).format(Number(value));
    }

    function formatPrice(offer) {

        const value = offer.analysis?.current_price ??
            offer.latestPrice?.price;

        return formatMoney(
            value,
            offer.currency,
            offer.market
        );
    }

    // ======================================
    // CREATE TEXT ELEMENT
    // ======================================

    function createText(tag, className, content) {

        const element = document.createElement(tag);

        if (className) {
            element.className = className;
        }

        element.textContent = content;

        return element;
    }

    // ======================================
    // PRICE ANALYSIS
    // ======================================

    function createAnalysisSection(offer) {

        const section = document.createElement("div");

        section.style.marginTop = "15px";
        section.style.paddingTop = "12px";
        section.style.borderTop = "1px solid #333";
        section.style.fontSize = "13px";

        const analysis = offer.analysis;

        if (!analysis) {

            section.textContent = "Price analysis unavailable.";

            return section;
        }

        if (analysis.status === "collecting_data") {

            section.textContent =
                "Collecting more price history for this store.";

            return section;
        }

        const rows = [
            {
                label: "Historical low",
                value: analysis.historical_low
            },
            {
                label: "Average price",
                value: analysis.average_price
            },
            {
                label: "Previous price",
                value: analysis.previous_price
            }
        ];

        rows.forEach(row => {

            if (row.value === null || row.value === undefined) {
                return;
            }

            const line = document.createElement("div");

            line.style.display = "flex";
            line.style.justifyContent = "space-between";
            line.style.gap = "10px";
            line.style.marginBottom = "7px";

            line.append(
                createText("span", "", row.label),
                createText(
                    "strong",
                    "",
                    formatMoney(
                        row.value,
                        offer.currency,
                        offer.market
                    )
                )
            );

            section.appendChild(line);
        });

        if (analysis.variation_percent !== null &&
            analysis.variation_percent !== undefined) {

            const variation = Number(analysis.variation_percent);

            const line = document.createElement("div");

            line.style.marginTop = "10px";
            line.style.fontWeight = "bold";

            line.style.color = variation < 0
                ? "#32c878"
                : variation > 0
                    ? "#ff9900"
                    : "#ffffff";

            line.textContent =
                `Price variation: ${variation > 0 ? "+" : ""}${variation}%`;

            section.appendChild(line);
        }

        if (analysis.new_historical_low) {

            const badge = createText(
                "div",
                "",
                "🔥 New historical low"
            );

            badge.style.color = "#32c878";
            badge.style.fontWeight = "bold";
            badge.style.marginTop = "10px";

            section.appendChild(badge);
        }

        return section;
    }

    // ======================================
    // STORE-TO-STORE PRICE COMPARISON
    // ======================================

    function createComparisonSection(offer) {

        const section = document.createElement("div");
        section.style.marginTop = "14px";
        section.style.padding = "12px";
        section.style.border = "1px solid #3a3a3a";
        section.style.borderRadius = "10px";
        section.style.fontSize = "13px";

        const comparisonOffers = offer.comparison?.offers;

        if (!Array.isArray(comparisonOffers)) {
            section.textContent = "Store comparison unavailable.";
            return section;
        }

        const validOffers = comparisonOffers
            .filter(item =>
                Number.isFinite(Number(item.price)) &&
                Number(item.price) > 0 &&
                item.currency === offer.currency
            )
            .sort((a, b) => Number(a.price) - Number(b.price));

        if (validOffers.length < 2) {
            section.textContent = "Waiting for another store to compare prices.";
            return section;
        }

        const best = validOffers[0];
        const current = validOffers.find(item =>
            Number(item.offer_id) === Number(offer.id)
        );

        if (!current) {
            section.textContent = "This offer is not included in the comparison.";
            return section;
        }

        const heading = createText(
            "div",
            "",
            `PRICE COMPARISON · ${validOffers.length} STORES`
        );
        heading.style.fontWeight = "bold";
        heading.style.color = "#ffb52e";
        heading.style.marginBottom = "9px";

        section.appendChild(heading);

        if (Number(current.offer_id) === Number(best.offer_id)) {

            const nextOffer = validOffers.find(item =>
                Number(item.offer_id) !== Number(current.offer_id)
            );

            const difference = Number(nextOffer.price) - Number(current.price);
            const percentage = difference / Number(nextOffer.price) * 100;

            const result = createText(
                "div",
                "",
                `You save ${formatMoney(difference, offer.currency, offer.market)} (${percentage.toFixed(2)}%) vs ${nextOffer.store}.`
            );

            result.style.color = "#32c878";
            result.style.fontWeight = "bold";
            section.appendChild(result);

        } else {

            const difference = Number(current.price) - Number(best.price);
            const percentage = difference / Number(current.price) * 100;

            const result = createText(
                "div",
                "",
                `Best price at ${best.store}: ${formatMoney(best.price, offer.currency, offer.market)}. Difference: ${formatMoney(difference, offer.currency, offer.market)} (${percentage.toFixed(2)}%).`
            );

            result.style.color = "#ffb52e";
            section.appendChild(result);
        }

        return section;
    }

    // ======================================
    // CREATE OFFER CARD
    // ======================================

    function createOfferCard(offer) {

        const card = document.createElement("div");
        card.className = "offer-card";

        // Best price indicator

        if (offer.isBestOffer) {

            const best = createText(
                "div",
                "",
                "🏆 BEST PRICE"
            );

            best.style.color = "#32c878";
            best.style.fontWeight = "bold";
            best.style.marginBottom = "12px";

            card.appendChild(best);
        }

        // Real product image only when supplied
        // by a non-test data source.

        if (
            offer.image_url &&
            offer.catalog_source !== "TEST"
        ) {

            const image = document.createElement("img");

            image.src = offer.image_url;
            image.alt = offer.name || "Product";
            image.loading = "lazy";

            image.style.width = "100%";
            image.style.height = "180px";
            image.style.objectFit = "contain";
            image.style.marginBottom = "15px";

            image.onerror = () => image.remove();

            card.appendChild(image);

        } else {

            const icon = createText(
                "div",
                "",
                getProductIcon(offer)
            );

            icon.style.fontSize = "38px";
            icon.style.marginBottom = "15px";

            card.appendChild(icon);
        }

        // Store

        const store = createText(
            "div",
            "store",
            offer.store || "Unknown Store"
        );

        // Product name

        const title = createText(
            "h3",
            "",
            offer.name || "Unnamed Product"
        );

        // Current price

        const price = createText(
            "p",
            "",
            formatPrice(offer)
        );

        price.style.fontSize = "20px";
        price.style.color = "#ff9900";
        price.style.fontWeight = "bold";
        price.style.margin = "15px 0";

        card.append(store, title, price);

        // Test notice

        const notice = createText(
            "p",
            "",
            offer.catalog_source === "TEST"
                ? "TEST DATA — NOT A LIVE OFFER"
                : "PRICE TRACKED BY WEBEOUT"
        );

        notice.style.fontSize = "11px";
        notice.style.fontWeight = "bold";
        notice.style.color = "#ffb52e";

        card.appendChild(notice);

        // Price analysis

        card.appendChild(createAnalysisSection(offer));

        // Store comparison

        card.appendChild(createComparisonSection(offer));

        // Product link only for non-test records.

        const url = offer.affiliate_url || offer.product_url;

        if (
            url &&
            offer.catalog_source !== "TEST" &&
            /^https?:\/\//i.test(url)
        ) {

            const link = document.createElement("a");

            link.href = url;
            link.target = "_blank";
            link.rel = "noopener noreferrer sponsored";
            link.textContent = "View Deal";

            link.style.display = "inline-block";
            link.style.marginTop = "15px";
            link.style.color = "#ff9900";
            link.style.fontWeight = "bold";

            card.appendChild(link);
        }

        return card;
    }

    // ======================================
    // RENDER OFFERS
    // ======================================

    function renderOffers() {

        if (!offersGrid) return;

        const filteredOffers = offers.filter(offer => {

            const searchText = currentSearch.toLowerCase();

            const name = (offer.name || "").toLowerCase();
            const store = (offer.store || "").toLowerCase();

            const matchesSearch =
                name.includes(searchText) ||
                store.includes(searchText);

            const matchesCategory =
                selectedCategory === "all" ||
                offer.category === selectedCategory;

            return matchesSearch && matchesCategory;
        });

        offersGrid.replaceChildren();

        if (filteredOffers.length === 0) {

            showMessage(
                "No offers found",
                "Try another search, category or market."
            );

            return;
        }

        filteredOffers.forEach(offer => {

            offersGrid.appendChild(
                createOfferCard(offer)
            );
        });
    }

    // ======================================
    // SEARCH
    // ======================================

    function searchProduct() {

        currentSearch = searchInput
            ? searchInput.value.trim().toLowerCase()
            : "";

        renderOffers();

        document.getElementById("offers")?.scrollIntoView({
            behavior: "smooth"
        });
    }

    if (searchButton) {
        searchButton.addEventListener("click", searchProduct);
    }

    if (searchInput) {

        searchInput.addEventListener("keydown", event => {

            if (event.key === "Enter") {
                searchProduct();
            }
        });
    }

    // ======================================
    // MARKET CHANGE
    // ======================================

    if (marketSelect) {

        marketSelect.addEventListener("change", () => {

            currentSearch = "";
            selectedCategory = "all";

            if (searchInput) {
                searchInput.value = "";
            }

            loadOffers();
        });
    }

    // ======================================
    // CATEGORY FILTER
    // ======================================

    categories.forEach(category => {

        category.addEventListener("click", () => {

            const categoryName =
                category.querySelector("h3")?.textContent.trim();

            selectedCategory = normalizeCategory(
                categoryName || "all"
            );

            renderOffers();

            document.getElementById("offers")?.scrollIntoView({
                behavior: "smooth"
            });
        });
    });

    // ======================================
    // INITIALIZATION
    // ======================================

    console.log("Webeout price analysis connected.");

    loadOffers();

});