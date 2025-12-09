// 初始化 Reveal.js
Reveal.initialize({
    hash: true,

    // ★★★ 核心修改 1：垂直不居中（你已经改了） ★★★
    center: false, 

    // ★★★ 核心修改 2：水平方向填满容器 ★★★
    // 将宽度设为你容器的最大宽度 (1600)，这样内容就会向左扩展，消除空白
    width: 1600,
    height: 900, // 保持 16:9 比例 (1600 * 9 / 16)

    // ★★★ 核心修改 3：减小边缘留白 ★★★
    // 默认是 0.1，改成 0.04 可以让内容更贴近边缘
    margin: -0.04,

    // 其他配置保持不变
    slideNumber: false,
    controls: true,
    progress: false,
    controls: false,   // false = 隐藏右下角的默认箭头
    navigationMode: 'linear',
    plugins: [ RevealMath.KaTeX ] 
});


let slidesData = [];

Reveal.on('ready', event => { initData(); renderHeader(); updateNavigation(); });
Reveal.on('slidechanged', event => { updateNavigation(); });

function initData() {
    const slides = document.querySelectorAll('.slides > section');
    let currentSectionTitle = "Untitled";
    slides.forEach((slide, index) => {
        if (slide.getAttribute('data-section')) currentSectionTitle = slide.getAttribute('data-section');
        slidesData.push({ index: index, sectionTitle: currentSectionTitle });
    });
}

function renderHeader() {
    const header = document.getElementById('beamer-header');
    header.innerHTML = '';
    let groupedSlides = {};
    let sectionOrder = [];
    slidesData.forEach(slide => {
        if (!groupedSlides[slide.sectionTitle]) { groupedSlides[slide.sectionTitle] = []; sectionOrder.push(slide.sectionTitle); }
        groupedSlides[slide.sectionTitle].push(slide);
    });
    sectionOrder.forEach(title => {
        const slidesInGroup = groupedSlides[title];
        const sectionEl = document.createElement('div');
        sectionEl.className = 'header-section';
        sectionEl.dataset.title = title;
        sectionEl.onclick = (e) => {
            if(e.target === sectionEl || e.target.classList.contains('header-section-title')) Reveal.slide(slidesInGroup[0].index);
        };
        sectionEl.innerHTML = `<div class="header-section-title">${title}</div>`;
        const dotsDiv = document.createElement('div'); dotsDiv.className = 'header-dots';
        slidesInGroup.forEach(slide => {
            const dot = document.createElement('div'); dot.className = 'dot'; dot.dataset.index = slide.index;
            dot.onclick = (e) => { e.stopPropagation(); Reveal.slide(slide.index); };
            dotsDiv.appendChild(dot);
        });
        sectionEl.appendChild(dotsDiv);
        header.appendChild(sectionEl);
    });
}

function updateNavigation() {
    const index = Reveal.getIndices().h;
    const total = Reveal.getTotalSlides();
    const slideNumEl = document.getElementById('slide-number');
    if(slideNumEl) slideNumEl.innerText = `${index + 1} / ${total}`;

    const currentSlideData = slidesData[index];
    if (!currentSlideData) return;

    document.querySelectorAll('.header-section').forEach(el => {
        el.classList.remove('active');
        if (el.dataset.title === currentSlideData.sectionTitle) el.classList.add('active');
    });
    document.querySelectorAll('.dot').forEach(dot => {
        dot.classList.remove('active');
        if (parseInt(dot.dataset.index) === index) dot.classList.add('active');
    });
}