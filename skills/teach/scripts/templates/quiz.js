/* teach 工作区自测组件：零依赖、离线可用、可打印。
 *
 * 用法：
 *   <ol class="quiz">
 *     <li data-answer="b">
 *       <p class="stem">题干</p>
 *       <ul class="opts">
 *         <li data-key="a">选项</li>
 *         <li data-key="b">选项</li>
 *       </ul>
 *       <p class="why">解析（答完后显示）</p>
 *     </li>
 *   </ol>
 *
 * 每题只能作答一次；答完所有题后在列表末尾插入小结。 */

(function () {
  "use strict";

  var SUMMARY = {
    perfect: "全对。这一节可以过了——下次会话我会用间隔复考来确认留存。",
    good: "基本掌握。错的那题我已经记进掌握度表，下次换个语境再考。",
    rough: "这一节还没稳。把错题的解析读一遍，然后直接问我——不要重读讲义，重读只会建起虚假的熟练感。",
  };

  function labelOf(li) {
    var key = li.dataset.key || "";
    var text = (li.textContent || "").trim().replace(/\s+/g, " ");
    return (key ? key + ". " : "") + text;
  }

  function grade(quiz, item, picked) {
    var answer = (item.dataset.answer || "").trim();
    var opts = item.querySelectorAll(".opts > li");
    var ok = (picked.dataset.key || "") === answer;

    item.classList.add("answered");
    quiz.classList.add("answered");

    Array.prototype.forEach.call(opts, function (o) {
      o.setAttribute("tabindex", "-1");
      o.setAttribute("aria-disabled", "true");
      if ((o.dataset.key || "") === answer) o.classList.add("correct");
    });

    if (!ok) {
      picked.classList.add("wrong");
      picked.setAttribute("aria-label", labelOf(picked) + "（答错）");
    } else {
      picked.setAttribute("aria-label", labelOf(picked) + "（答对）");
    }

    return ok;
  }

  function finish(quiz, asked, correct) {
    if (quiz.querySelector(".quiz-summary")) return;

    var p = document.createElement("p");
    p.classList.add("quiz-summary");
    p.setAttribute("role", "status");

    var ratio = asked ? correct / asked : 0;
    if (asked && correct === asked) p.classList.add("perfect");
    else if (ratio < 0.6) p.classList.add("rough");

    p.textContent = "得分 " + correct + "/" + asked + "　" +
      (asked && correct === asked ? SUMMARY.perfect : ratio < 0.6 ? SUMMARY.rough : SUMMARY.good);

    var host = quiz.parentNode;
    if (host) host.insertBefore(p, quiz.nextSibling);
    else document.body.appendChild(p);
  }

  function init(quiz) {
    var items = Array.prototype.slice.call(quiz.children).filter(function (el) {
      return el.tagName === "LI";
    });
    if (!items.length) return;

    var asked = 0;
    var correct = 0;

    items.forEach(function (item) {
      var opts = item.querySelectorAll(".opts > li");
      if (!opts.length) return;

      Array.prototype.forEach.call(opts, function (opt) {
        opt.setAttribute("role", "button");
        opt.setAttribute("tabindex", "0");

        function pick() {
          if (item.classList.contains("answered")) return;
          asked += 1;
          if (grade(quiz, item, opt)) correct += 1;
          finish(quiz, asked, correct);
        }

        opt.addEventListener("click", pick);
        opt.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
            e.preventDefault();
            pick();
          }
        });
      });
    });
  }

  function boot() {
    Array.prototype.forEach.call(document.querySelectorAll("ol.quiz"), init);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
