/* Jesse Mattila — jaettu sivustologiikka */
(function () {
  // skrollipalkki
  var bar = document.getElementById('scrollProgress');
  if (bar) {
    addEventListener('scroll', function () {
      var h = document.body.scrollHeight - innerHeight;
      bar.style.width = (h > 0 ? (scrollY / h) * 100 : 0) + '%';
    }, { passive: true });
  }

  // sisääntulot
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); } });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.fade-in').forEach(function (el) { io.observe(el); });

  // laskurit
  document.querySelectorAll('[data-count]').forEach(function (el) {
    var target = parseFloat(el.dataset.count), sfx = el.dataset.suffix || '', pfx = el.dataset.prefix || '';
    var o = new IntersectionObserver(function (es) {
      es.forEach(function (x) {
        if (!x.isIntersecting) return;
        o.disconnect();
        var start = null, dur = 1400;
        function step(t) {
          if (!start) start = t;
          var p = Math.min((t - start) / dur, 1);
          var v = Math.floor((1 - Math.pow(1 - p, 3)) * target);
          el.textContent = pfx + v.toLocaleString('fi-FI') + sfx;
          if (p < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      });
    }, { threshold: 0.5 });
    o.observe(el);
  });

  // agenttiputken elävä vaihe
  var nodes = Array.prototype.slice.call(document.querySelectorAll('.pipeline-flow .pipe-step'));
  if (nodes.length && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var i = 0;
    setInterval(function () {
      nodes.forEach(function (n) { n.classList.remove('on'); });
      nodes[i].classList.add('on');
      i = (i + 1) % nodes.length;
    }, 1100);
  }

  // mobiilivalikko
  var burger = document.querySelector('.hamburger'), links = document.querySelector('.nav-links');
  if (burger && links) burger.addEventListener('click', function () { links.classList.toggle('active'); });
})();
