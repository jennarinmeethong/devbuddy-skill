(() => {
  const slides = [...document.querySelectorAll('.slide')];
  const scroller = document.querySelector('.slides');
  const previous = document.querySelector('[data-prev]');
  const next = document.querySelector('[data-next]');
  const current = document.querySelector('[data-current]');
  const total = document.querySelector('[data-total]');
  const progress = document.querySelector('[data-progress]');
  const notes = document.querySelector('.speaker-notes');
  const notesButton = document.querySelector('[data-notes]');
  const noteContent = document.querySelector('[data-note-content]');
  let activeIndex = 0;

  total.textContent = String(slides.length).padStart(2, '0');

  const update = (index) => {
    activeIndex = Math.max(0, Math.min(index, slides.length - 1));
    const activeSlide = slides[activeIndex];
    slides.forEach((slide, slideIndex) => slide.classList.toggle('is-active', slideIndex === activeIndex));
    current.textContent = String(activeIndex + 1).padStart(2, '0');
    progress.style.width = `${((activeIndex + 1) / slides.length) * 100}%`;
    previous.disabled = activeIndex === 0;
    next.disabled = activeIndex === slides.length - 1;
    noteContent.textContent = activeSlide.dataset.note || '';
    document.title = `${activeSlide.dataset.title} · DevBuddy`;
  };

  const move = (offset) => {
    const target = Math.max(0, Math.min(activeIndex + offset, slides.length - 1));
    slides[target].scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  previous.addEventListener('click', () => move(-1));
  next.addEventListener('click', () => move(1));

  const observer = new IntersectionObserver((entries) => {
    const visible = entries
      .filter(entry => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (visible) update(slides.indexOf(visible.target));
  }, { root: scroller, threshold: [0.55, 0.7] });
  slides.forEach(slide => observer.observe(slide));

  const toggleNotes = (force) => {
    const isOpen = force ?? !notes.classList.contains('is-open');
    notes.classList.toggle('is-open', isOpen);
    notesButton.setAttribute('aria-pressed', String(isOpen));
  };
  notesButton.addEventListener('click', () => toggleNotes());
  document.querySelector('[data-close-notes]').addEventListener('click', () => toggleNotes(false));

  document.querySelector('[data-fullscreen]').addEventListener('click', async () => {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen?.();
  });

  document.addEventListener('keydown', (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (['ArrowDown', 'ArrowRight', 'PageDown', ' '].includes(event.key)) { event.preventDefault(); move(1); }
    if (['ArrowUp', 'ArrowLeft', 'PageUp'].includes(event.key)) { event.preventDefault(); move(-1); }
    if (event.key === 'Home') { event.preventDefault(); slides[0].scrollIntoView({ behavior: 'smooth' }); }
    if (event.key === 'End') { event.preventDefault(); slides.at(-1).scrollIntoView({ behavior: 'smooth' }); }
    if (event.key.toLowerCase() === 'n') toggleNotes();
    if (event.key.toLowerCase() === 'f') document.querySelector('[data-fullscreen]').click();
    if (event.key === 'Escape') toggleNotes(false);
  });

  update(0);
})();
