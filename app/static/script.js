document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.tab');
    const slider = document.querySelector('.tab-slider');

    if (tabs.length > 0 && slider) {
        function moveSlider(target) {
            slider.style.width = `${target.offsetWidth}px`;
            slider.style.transform = `translateX(${target.offsetLeft}px)`;
        }

        tabs.forEach(tab => {
            tab.addEventListener('mouseenter', () => moveSlider(tab));
        });

        const tabsContainer = document.querySelector('.tabs');
        tabsContainer.addEventListener('mouseleave', () => {
            const activeTab = document.querySelector('.tab.active') || tabs[0];
            moveSlider(activeTab);
        });

        const initialActiveTab = document.querySelector('.tab.active') || tabs[0];
        moveSlider(initialActiveTab);
    }
});
