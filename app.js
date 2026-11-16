
// ==========================================
// WEBEOUT — CONNECTED PRODUCT SEARCH SYSTEM
// API + SQLITE
// ==========================================

document.addEventListener("DOMContentLoaded", () => {

    const API_URL = "https://webeout.onrender.com".replace(/\/+$/, "");

    const searchInput = document.getElementById("search");
    const searchButton = document.querySelector(".search-box .button");
    const marketSelect = document.getElementById("market");
    const categories = document.querySelectorAll(".category");
    const offersGrid = document.querySelector(".offers-grid");

    let selectedCategory = "all";
    let currentSearch = "";
    let products = [];
    let requestVersion = 0;

    // ======================================
    // CONFIGURAÇÃO DE CATEGORIAS
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

    function getMarket() {
        return marketSelect ? marketSelect.value : "US";
    }

    // ======================================
    // ÍCONES DOS PRODUTOS
    // ======================================

    function getProductIcon(product) {

        const text = (
            product.name + " " + (product.category || "")
        ).toLowerCase();

        if (text.includes("headphone") || text.includes("kopfhörer")) {
            return "🎧";
        }

        if (text.includes("keyboard") || text.includes("tastatur")) {
            return "⌨️";
        }

        if (text.includes("watch") || text.includes("smartwatch")) {
            return "⌚";
        }

        if (text.includes("gaming")) {
            return "🎮";
        }

        return "📦";
    }

    // ======================================
    // MENSAGENS DO SISTEMA
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
    // CONSULTAR HISTÓRICO DE PREÇOS
    // ======================================

    async function getLatestPrice(productCode) {

        try {

            const response = await fetch(
                `${API_URL}/products/${encodeURIComponent(productCode)}/history`
            );

            if (!response.ok) {
                return null;
            }

            const history = await response.json();

            if (!Array.isArray(history) || history.length === 0) {
                return null;
            }

            return history[history.length - 1];

        } catch (error) {

            console.error(
                "Error loading price history:",
                productCode,
                error
            );

            return null;
        }
    }

    // ======================================
    // BUSCAR PRODUTOS NA API
    // ======================================

    async function loadProducts() {

        if (!offersGrid) return;

        const version = ++requestVersion;
        const market = getMarket();

        showMessage(
            "Loading products...",
            "Connecting to the Webeout database.",
            "⏳"
        );

        try {

            const response = await fetch(
                `${API_URL}/products?market=${encodeURIComponent(market)}`
            );

            if (!response.ok) {
                throw new Error("Could not load products from API.");
            }

            const data = await response.json();

            if (version !== requestVersion) return;

            if (!Array.isArray(data)) {
                throw new Error("Invalid API response.");
            }

            const productsWithPrices = await Promise.all(
                data.map(async product => {

                    const latestPrice = await getLatestPrice(
                        product.product_code
                    );

                    return {
                        ...product,
                        latestPrice
                    };

                })
            );

            if (version !== requestVersion) return;

            products = productsWithPrices;

            renderProducts();

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
    // CRIAR CARD DO PRODUTO
    // ======================================

    function createProductCard(product) {

        const card = document.createElement("div");
        card.className = "offer-card";

        const icon = document.createElement("div");
        icon.style.fontSize = "38px";
        icon.style.marginBottom = "15px";
        icon.textContent = getProductIcon(product);

        const store = document.createElement("div");
        store.className = "store";
        store.textContent = product.store || "Unknown Store";

        const title = document.createElement("h3");
        title.textContent = product.name;

        const price = document.createElement("p");

        price.style.fontSize = "20px";
        price.style.color = "#ff9900";
        price.style.fontWeight = "bold";
        price.style.margin = "15px 0";

        if (product.latestPrice) {

            price.textContent = new Intl.NumberFormat(
                product.market === "DE" ? "de-DE" : "en-US",
                {
                    style: "currency",
                    currency: product.currency
                }
            ).format(product.latestPrice.price);

        } else {

            price.textContent = "Price history unavailable";

        }

        const notice = document.createElement("p");

        notice.style.color = "#ffb52e";
        notice.style.fontSize = "11px";
        notice.style.fontWeight = "bold";

        notice.textContent =
            "DATABASE RECORD — NOT A VERIFIED LIVE OFFER";

        card.append(
            icon,
            store,
            title,
            price,
            notice
        );

        return card;
    }

    // ======================================
    // EXIBIR PRODUTOS
    // ======================================

    function renderProducts() {

        if (!offersGrid) return;

        const filteredProducts = products.filter(product => {

            const searchText = currentSearch.toLowerCase();

            const matchesSearch =
                product.name.toLowerCase().includes(searchText) ||
                (product.store || "").toLowerCase().includes(searchText);

            const matchesCategory =
                selectedCategory === "all" ||
                product.category === selectedCategory;

            return matchesSearch && matchesCategory;

        });

        offersGrid.replaceChildren();

        if (filteredProducts.length === 0) {

            showMessage(
                "No products found",
                "Try another search, category or market."
            );

            return;
        }

        filteredProducts.forEach(product => {

            const card = createProductCard(product);
            offersGrid.appendChild(card);

        });

    }

    // ======================================
    // PESQUISA
    // ======================================

    function searchProduct() {

        currentSearch = searchInput
            ? searchInput.value.trim().toLowerCase()
            : "";

        renderProducts();

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
    // TROCA DE MERCADO
    // ======================================

    if (marketSelect) {

        marketSelect.addEventListener("change", () => {

            currentSearch = "";
            selectedCategory = "all";

            if (searchInput) {
                searchInput.value = "";
            }

            loadProducts();

        });

    }

    // ======================================
    // FILTRO DE CATEGORIAS
    // ======================================

    categories.forEach(category => {

        category.addEventListener("click", () => {

            const categoryName =
                category.querySelector("h3")?.textContent.trim();

            selectedCategory = normalizeCategory(
                categoryName || "all"
            );

            renderProducts();

            document.getElementById("offers")?.scrollIntoView({
                behavior: "smooth"
            });

        });

    });

    // ======================================
    // INICIALIZAÇÃO
    // ======================================

    console.log("Webeout connected to API.");

    loadProducts();

});
