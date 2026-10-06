// Local-only response provider: no networking or persistent storage.
(() => {
  const { catalog, normalize } = window.AXPORTChatI18n;
  // Match all localized recommendations to the same stable answer index.
  const lookup = new Map();
  Object.values(catalog).forEach(pack => {
    [...pack.questions.home, ...pack.questions.workspace].forEach((q, i) => lookup.set(q, i));
  });
  function getResponse(question, locale = 'ko') {
    const pack = catalog[normalize(locale)];
    return pack.answers[lookup.get(question)] || pack.fallback;
  }
  let next = null;
  window.AXPORTChatDemo = Object.freeze({
    questions: catalog.ko.questions,
    getResponse,
    configureNext(options = {}) {
      next = { delayMs: Math.max(0, Math.min(60000, Number(options.delayMs) || 0)), fail: options.fail === true };
    },
    respond(question, locale = 'ko') {
      const scenario = next || { delayMs:850, fail:false };
      next = null;
      return new Promise((resolve, reject) => setTimeout(() => {
        if (scenario.fail) reject(new Error('Local demo failure'));
        else resolve(getResponse(question, locale));
      }, scenario.delayMs));
    },
  });
})();
