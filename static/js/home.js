/* AXPORT landing, test1 content + original cinematic motion. */
(() => {
  "use strict";

  const menuButton = document.querySelector(".menu-toggle");
  const mobileMenu = document.querySelector("#mobile-nav");
  const transition = document.querySelector(".app-transition");
  const header = document.querySelector("#site-header");
  const hero = document.querySelector("#hero");
  const video = document.querySelector(".hero-video");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let navigating = false;
  let scrollScheduled = false;

  // Mobile navigation remains usable independently of animations.
  function closeMenu() {
    if (!menuButton || !mobileMenu) return;
    mobileMenu.hidden = true;
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.setAttribute("aria-label", "메뉴 열기");
    menuButton.innerHTML = '<i class="ph ph-list" aria-hidden="true"></i>';
  }

  menuButton?.addEventListener("click", () => {
    if (!mobileMenu) return;
    const opening = mobileMenu.hidden;
    mobileMenu.hidden = !opening;
    menuButton.setAttribute("aria-expanded", String(opening));
    menuButton.setAttribute("aria-label", opening ? "메뉴 닫기" : "메뉴 열기");
    menuButton.innerHTML = `<i class="ph ${opening ? "ph-x" : "ph-list"}" aria-hidden="true"></i>`;
  });

  mobileMenu?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeMenu);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && mobileMenu && !mobileMenu.hidden) {
      closeMenu();
      menuButton?.focus();
    }
  });

  // One floating nav surface changes to a light treatment in the story area.
  function updateScrollStyle() {
    scrollScheduled = false;
    if (!header || !hero) return;
    const boundary = Math.max(130, hero.offsetHeight - 135);
    const isPastHero = window.scrollY >= boundary;
    header.classList.toggle("is-scrolled", isPastHero);
  }
  window.addEventListener("scroll", () => {
    if (scrollScheduled) return;
    scrollScheduled = true;
    window.requestAnimationFrame(updateScrollStyle);
  }, { passive: true });
  window.addEventListener("resize", updateScrollStyle, { passive: true });
  updateScrollStyle();

  // Keep the real /app link functional even if this script fails or JS is off.
  document.querySelectorAll("[data-launch-app]").forEach((link) => {
    link.addEventListener("click", (event) => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
      if (!transition || navigating) return;
      event.preventDefault();
      navigating = true;
      transition.hidden = false;
      document.body.setAttribute("aria-busy", "true");
      window.requestAnimationFrame(() =>
        window.requestAnimationFrame(() => window.location.assign(link.href))
      );
    });
  });
  window.addEventListener("pageshow", () => {
    navigating = false;
    if (transition) transition.hidden = true;
    document.body.removeAttribute("aria-busy");
    closeMenu();
    updateScrollStyle();
  });

  // Scroll reveals and no-motion fallback; content remains visible without JS.
  if ("IntersectionObserver" in window && !reducedMotion.matches) {
    document.documentElement.classList.add("motion-ready");
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: "0px 0px 10px 0px" });
    document.querySelectorAll(".reveal").forEach((element) => observer.observe(element));
  }

  // Pause background film when hidden or when the user requests less motion.
  function syncVideo() {
    if (!video) return;
    if (document.hidden || reducedMotion.matches) {
      video.pause();
    } else {
      const playing = video.play();
      if (playing?.catch) playing.catch(() => {}); // poster image remains visible
    }
  }
  document.addEventListener("visibilitychange", syncVideo);
  if (reducedMotion.addEventListener) reducedMotion.addEventListener("change", syncVideo);
  syncVideo();
  // Accessible compact language menu. The existing shared i18n select remains
  // in the DOM, so the workspace keeps using the same stored language.
  const picker = document.querySelector("#language-picker");
  const pickerButton = document.querySelector("#language-trigger");
  const pickerMenu = document.querySelector("#language-menu");
  const nativeSelect = document.querySelector("#axp-language");
  const langShort = {ko:"KO",en:"EN",zh:"中文",ja:"日本語"};
  function closeLanguage(restoreFocus = false) {
    if (!pickerButton || !pickerMenu) return;
    pickerMenu.hidden = true;
    pickerButton.setAttribute("aria-expanded", "false");
    if (restoreFocus) pickerButton.focus();
  }
  function openLanguage(focusFirst = false) {
    if (!pickerButton || !pickerMenu) return;
    pickerMenu.hidden = false;
    pickerButton.setAttribute("aria-expanded", "true");
    if (focusFirst) pickerMenu.querySelector('[aria-checked="true"]')?.focus();
  }
  function updateLanguagePicker() {
    const current = window.AXPI18n?.language || nativeSelect?.value || "ko";
    const label = pickerButton?.querySelector(".language-current");
    if (label) label.textContent = langShort[current] || "KO";
    pickerMenu?.querySelectorAll("[data-language]").forEach((option) => {
      option.setAttribute("aria-checked", String(option.dataset.language === current));
    });
  }
  pickerButton?.addEventListener("click", () => {
    if (!pickerMenu) return;
    if (pickerMenu.hidden) { closeMenu(); openLanguage(); }
    else closeLanguage();
  });
  pickerMenu?.querySelectorAll("[data-language]").forEach((option) => {
    option.addEventListener("click", () => {
      const selected = option.dataset.language;
      if (window.AXPI18n) window.AXPI18n.setLanguage(selected);
      else if (nativeSelect) {
        nativeSelect.value = selected;
        nativeSelect.dispatchEvent(new Event("change", {bubbles:true}));
      }
      updateLanguagePicker();
      closeLanguage(true);
    });
  });
  pickerMenu?.addEventListener("keydown", (event) => {
    const options = [...pickerMenu.querySelectorAll("[data-language]")];
    const index = options.indexOf(document.activeElement);
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      options[(index + options.length + (event.key === "ArrowDown" ? 1 : -1)) % options.length]?.focus();
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      options[event.key === "Home" ? 0 : options.length-1]?.focus();
    } else if (event.key === "Escape") {
      closeLanguage(true);
    }
  });
  pickerButton?.addEventListener("keydown", (event) => {
    if (["ArrowDown", "ArrowUp"].includes(event.key)) {
      event.preventDefault();
      openLanguage(true);
    }
  });
  document.addEventListener("pointerdown", (event) => {
    if (picker && !picker.contains(event.target)) closeLanguage();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && pickerMenu && !pickerMenu.hidden) closeLanguage(true);
  });
  window.addEventListener("axp:language-changed", updateLanguagePicker);
  updateLanguagePicker();

  // Process previews loop only while visible; reduced-motion users see the final state.
  const steps = [...document.querySelectorAll(".step-card")];
  if(steps.length && "IntersectionObserver" in window) {
    const stepObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => entry.target.classList.toggle("is-demo-running",entry.isIntersecting));
    },{threshold:0.3});
    steps.forEach(step=>stepObserver.observe(step));
  } else steps.forEach(step=>step.classList.add("is-demo-running"));


  // Shared, full-bleed background image for the five criteria.
  // Images are siblings filling the entire rounded rectangle, never children
  // of an individual panel; hovering any panel cross-fades the full canvas.
  const criteriaSection = document.querySelector("#features.criteria-section");
  const criteriaStage = document.querySelector("#criteria-stage");
  if (criteriaSection && criteriaStage) {
    const panes = Array.from(criteriaStage.querySelectorAll("[data-criteria]"));
    const images = Array.from(criteriaStage.querySelectorAll("[data-criteria-image]"));
    const defaultImage = criteriaStage.querySelector("[data-criteria-default]");
    const supportsHover = window.matchMedia("(hover:hover) and (pointer:fine)");

    // Use the provided asset directly. Never substitute the hero poster here.
    // The matching CSS background covers the stage before JS is ready.
    if (defaultImage) {
      criteriaStage.dataset.defaultImageFilename = "feature-default.jpg";
      criteriaStage.dataset.defaultImageStatus = "loading";
      defaultImage.addEventListener("load", () => {
        criteriaStage.dataset.defaultImageStatus = "ready";
      });
      defaultImage.addEventListener("error", () => {
        criteriaStage.dataset.defaultImageStatus = "missing";
        // Check static/assets/feature-default.jpg if the image cannot load.
      });
      if (defaultImage.complete) {
        criteriaStage.dataset.defaultImageStatus = defaultImage.naturalWidth ? "ready" : "missing";
      }
    }

    function setCriterion(index) {
      const hasSelection = Number.isInteger(index) && index >= 0 && index < panes.length;
      images.forEach((img, i) => img.classList.toggle("is-current", hasSelection && i === index));
      panes.forEach((pane, i) => {
        const selected = hasSelection && i === index;
        pane.classList.toggle("is-current", selected);
        pane.setAttribute("aria-pressed", String(selected));
      });
      criteriaStage.dataset.activeCriterion = hasSelection ? String(index) : "none";
    }

    panes.forEach((pane, index) => {
      pane.addEventListener("pointerenter", () => {
        if (supportsHover.matches) setCriterion(index);
      });
      pane.addEventListener("focus", () => setCriterion(index));
      pane.addEventListener("click", () => setCriterion(index));
    });
    criteriaStage.addEventListener("pointerleave", () => {
      // Clicking a panel can leave it focused: mouse exit still restores the
      // image-default background (keyboard :focus-visible remains accessible).
      if (supportsHover.matches && !criteriaStage.querySelector(".criteria-pane:focus-visible")) setCriterion(-1);
    });
    criteriaStage.addEventListener("focusout", (event) => {
      if (!criteriaStage.contains(event.relatedTarget) && !criteriaStage.matches(":hover")) setCriterion(-1);
    });
    setCriterion(-1);

    // Heading rises first; a rounded clipping mask reveals the unscaled
    // photograph from center to edges, then the five text panels fade in.
    if ("IntersectionObserver" in window && !reducedMotion.matches) {
      document.documentElement.classList.add("criteria-motion-ready");
      const criteriaObserver = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            criteriaSection.classList.add("is-visible");
            criteriaObserver.disconnect();
            break;
          }
        }
      }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
      criteriaObserver.observe(criteriaSection);
    } else {
      criteriaSection.classList.add("is-visible");
    }
  }
})();
