// 「黒字なのに、お金が残らない会社の共通点」10分セミナー資料 生成スクリプト
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa6");
const { applyTheme } = require("/root/.claude/skills/synced/4c0a959d-5b77-4339-afba-71634442de6d_b23410a0-5155-4ff7-a1bf-acab293a2ac0/pptx/scripts/apply_theme.js");

const OUT = process.argv[2] || "deck.pptx";
const PHOTO = "/home/user/kentakoseki0719/assets/koseki.jpg";

const HEX = {
  ink: "1F2B3A", navy: "16324F", white: "FFFFFF", tint: "EEF2F7",
  navyDeep: "0E2240", gold: "B08D3C", red: "B23A2E", inkSoft: "4A5768",
  goldBright: "C9A45C", slate: "8A99AD",
};
const THEME = {
  name: "Sphenos Finance",
  headFontFace: "Yu Gothic",
  bodyFontFace: "Yu Gothic",
  colors: {
    dk1: HEX.ink, lt1: HEX.white, dk2: HEX.navy, lt2: HEX.tint,
    accent1: HEX.navyDeep, accent2: HEX.gold, accent3: HEX.red,
    accent4: HEX.inkSoft, accent5: HEX.goldBright, accent6: HEX.slate,
    hlink: HEX.navy, folHlink: HEX.inkSoft,
  },
};

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
  pres.title = "黒字なのに、お金が残らないのはなぜ？";
  pres.subject = "黒字なのに、お金が残らない会社の共通点（10分セミナー）";
  pres.author = "株式会社スフェノス 小関健太";
  pres.company = "株式会社スフェノス";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  const W = 13.333, M = 0.6, CW = W - 2 * M;

  // ---------- Layouts ----------
  pres.defineSlideMaster({
    title: "TITLE_DARK",
    background: { color: C.accent1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 1.35, w: 7.6, h: 1.9, fontSize: 40, bold: true, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "subtitle", type: "body", x: 0.8, y: 3.35, w: 7.6, h: 0.6, fontSize: 24, bold: true, color: C.accent5, valign: "top", align: "left", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: C.background1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: M, y: 0.35, w: CW, h: 0.95, fontSize: 34, bold: true, color: C.text2, valign: "middle", margin: 0 }, text: "" } },
      { text: { text: "株式会社スフェノス｜黒字なのに、お金が残らない会社の共通点", options: { x: M, y: 6.98, w: 8, h: 0.3, fontSize: 11, color: C.accent6, margin: 0 } } },
    ],
    slideNumber: { x: 12.13, y: 6.98, w: 0.6, h: 0.3, fontSize: 11, color: C.accent6, align: "right", margin: 0 },
  });
  pres.defineSlideMaster({
    title: "CLOSING_DARK",
    background: { color: C.accent1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: M, y: 0.45, w: CW, h: 1.0, fontSize: 40, bold: true, color: C.background1, valign: "middle", margin: 0 }, text: "" } },
    ],
    slideNumber: { x: 12.13, y: 6.98, w: 0.6, h: 0.3, fontSize: 11, color: C.accent6, align: "right", margin: 0 },
  });

  const card = (s, name, x, y, w, h, fill, extra = {}) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { objectName: name, x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { type: "none" }, ...extra });
  const txt = (s, name, text, o) => s.addText(text, { objectName: name, isTextBox: true, margin: 0, ...o });
  const badge = (s, name, label, x, y, d, fill, color, fontSize) => {
    s.addShape(pres.shapes.OVAL, { objectName: name + "_circle", x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" } });
    txt(s, name + "_label", label, { x, y, w: d, h: d, align: "center", valign: "middle", fontSize, bold: true, color });
  };
  const notes = (s, time, total, body) => s.addNotes(`【目安時間】${time}（累計 ${total}）\n\n${body}`);

  // icons
  const I = {
    wallet: await icon(fa.FaWallet, HEX.white),
    invoice: await icon(fa.FaFileInvoice, HEX.navy),
    boxes: await icon(fa.FaBoxesStacked, HEX.navy),
    bank: await icon(fa.FaBuildingColumns, HEX.navy),
    factory: await icon(fa.FaIndustry, HEX.navy),
  };
  const face = await sharp(PHOTO).extract({ left: 330, top: 20, width: 300, height: 300 }).resize(400, 400).jpeg({ quality: 88 }).toBuffer();
  const faceData = "image/jpeg;base64," + face.toString("base64");

  // ================= Slide 1 =================
  pres.addSection({ title: "導入" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "導入" });
  txt(s, "kicker", "経営者のための10分セミナー｜黒字なのに、お金が残らない会社の共通点", { x: 0.8, y: 0.7, w: 11.7, h: 0.4, fontSize: 15, color: C.accent5 });
  s.addText("黒字なのに、\nお金が残らないのはなぜ？", { placeholder: "title" });
  s.addText("利益500万円でも、通帳が100万円減る理由", { placeholder: "subtitle" });
  card(s, "question_card", 0.8, 4.3, 7.6, 1.35, "24405F");
  txt(s, "question", "去年より利益が出たのに、通帳が増えていない。\nそんな経験はありませんか？", { x: 1.1, y: 4.3, w: 7.1, h: 1.35, fontSize: 21, color: C.background1, valign: "middle", lineSpacingMultiple: 1.2 });
  s.addImage({ objectName: "speaker_photo", data: faceData, x: 0.8, y: 6.0, w: 0.9, h: 0.9, rounding: true, altText: "講師 小関健太" });
  txt(s, "speaker", "株式会社スフェノス　代表　小関 健太", { x: 1.9, y: 6.0, w: 6.0, h: 0.9, fontSize: 18, color: C.background1, valign: "middle" });
  // right: two stat tiles
  card(s, "stat_profit_card", 9.0, 1.35, 3.73, 2.0, C.background1);
  txt(s, "stat_profit_label", "1年間の利益", { x: 9.3, y: 1.55, w: 3.2, h: 0.4, fontSize: 18, color: C.accent4 });
  txt(s, "stat_profit_value", "＋500万円", { x: 9.3, y: 2.0, w: 3.2, h: 1.0, fontSize: 44, bold: true, color: C.text2 });
  card(s, "stat_cash_card", 9.0, 3.65, 3.73, 2.0, C.background1);
  txt(s, "stat_cash_label", "同じ1年の通帳の増減", { x: 9.3, y: 3.85, w: 3.2, h: 0.4, fontSize: 18, color: C.accent4 });
  txt(s, "stat_cash_value", "−100万円", { x: 9.3, y: 4.3, w: 3.2, h: 1.0, fontSize: 44, bold: true, color: C.accent3 });
  notes(s, "0:45", "0:45",
`皆さん、こんにちは。株式会社スフェノスの小関です。今日は10分だけ、会社のお金の話をさせてください。

まず、ひとつ質問です。
去年より利益が出たのに、通帳が増えていない。そんな経験はありませんか？
（少し間を取る）

実はこれ、珍しいことではありません。利益が500万円出ていても、通帳が100万円減る。こういうことは、普通に起こります。
今日はその理由と、自社ではどこを確認すればいいのかをお話しします。`);

  // ================= Slide 2 =================
  pres.addSection({ title: "仕組み" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "仕組み" });
  s.addText("利益と通帳残高は、動く時期が違う", { placeholder: "title" });
  const ex = [
    { n: "例1", scene: "100万円を売り上げた。\nでも、入金は来月", p: "＋100万円", pc: C.text2, c: "±0円", cc: C.accent3,
      note: "※まだ入金されていない売上を「売掛金」といいます。\n　（説明のため、仕入などの経費は省略）" },
    { n: "例2", scene: "借入金の元本を\n100万円返した", p: "±0円", pc: C.text2, c: "−100万円", cc: C.accent3,
      note: "※元本の返済は経費になりません。\n　（利息の部分は経費になります）" },
  ];
  ex.forEach((e, i) => {
    const x = M + i * (5.86 + 0.4), y = 1.6, w = 5.86;
    card(s, `ex${i + 1}_card`, x, y, w, 4.95, C.background2);
    badge(s, `ex${i + 1}_badge`, e.n, x + 0.35, y + 0.4, 0.8, C.text2, C.background1, 16);
    txt(s, `ex${i + 1}_scene`, e.scene, { x: x + 1.4, y: y + 0.25, w: w - 1.7, h: 1.1, fontSize: 23, bold: true, color: C.text1, valign: "middle" });
    [["利益の計算", e.p, e.pc], ["今月の通帳", e.c, e.cc]].forEach(([lab, val, col], j) => {
      const ty = y + 1.6 + j * 1.3;
      card(s, `ex${i + 1}_tile${j + 1}`, x + 0.35, ty, w - 0.7, 1.1, C.background1);
      txt(s, `ex${i + 1}_tile${j + 1}_label`, lab, { x: x + 0.65, y: ty, w: 2.2, h: 1.1, fontSize: 20, color: C.accent4, valign: "middle" });
      txt(s, `ex${i + 1}_tile${j + 1}_value`, val, { x: x + 2.6, y: ty, w: w - 3.25, h: 1.1, fontSize: 36, bold: true, color: col, align: "right", valign: "middle" });
    });
    txt(s, `ex${i + 1}_note`, e.note, { x: x + 0.35, y: y + 4.2, w: w - 0.7, h: 0.6, fontSize: 13, color: C.accent4, valign: "top" });
  });
  notes(s, "1:15", "2:00",
`最初に、いちばん大事なことをお伝えします。利益と通帳残高は、動く時期が違います。

左の例を見てください。今月、100万円の仕事を納めて請求しました。売上は今月の数字に入るので、利益の計算ではプラス100万円です。でも、入金が来月なら、今月の通帳は1円も増えていません。

右の例は逆です。借入金の元本を100万円返しました。通帳からは確かに100万円出ていきます。でも、元本の返済は経費になりません。だから利益は減らないんです。ちなみに、利息の部分は経費になります。

つまり、利益の計算と通帳の動きは、もともと別のタイミングで動いている。ここを押さえておくと、この先の話がすっと入ってきます。`);

  // ================= Slide 3 (waterfall) =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "仕組み" });
  s.addText("利益500万円でも、現金は100万円減る", { placeholder: "title" });
  const steps = [
    { label: "税引後利益", v: 500, kind: "up" },
    { label: "減価償却費の\n足し戻し", v: 100, kind: "up" },
    { label: "売掛金・在庫\nの増加", v: -300, kind: "down" },
    { label: "借入元本の返済\n・設備購入", v: -400, kind: "down" },
    { label: "現金の増減", v: null, kind: "total" },
  ];
  const X0 = M, XW = 8.4, colW = XW / steps.length, barW = 1.0;
  const VMAX = 600, VMIN = -100, YT = 1.75, YB = 4.75, sc = (YB - YT) / (VMAX - VMIN);
  const yOf = (v) => YT + (VMAX - v) * sc;
  // zero line
  s.addShape(pres.shapes.LINE, { objectName: "zero_line", x: X0, y: yOf(0), w: XW, h: 0, line: { color: C.accent6, width: 1 } });
  txt(s, "zero_label", "0", { x: X0 - 0.35, y: yOf(0) - 0.15, w: 0.25, h: 0.3, fontSize: 12, color: C.accent6, align: "right" });
  let run = 0;
  const totalCheck = steps.filter((t) => t.v !== null).reduce((a, t) => a + t.v, 0);
  if (totalCheck !== -100) throw new Error("waterfall total mismatch " + totalCheck);
  steps.forEach((st, i) => {
    const cx = X0 + i * colW + colW / 2;
    let from, to, fill;
    if (st.kind === "total") { from = 0; to = run; fill = C.accent3; }
    else { from = run; to = run + st.v; run = to; fill = st.kind === "up" ? C.text2 : C.accent6; }
    const top = yOf(Math.max(from, to)), bot = yOf(Math.min(from, to));
    s.addShape(pres.shapes.RECTANGLE, { objectName: `bar${i + 1}`, x: cx - barW / 2, y: top, w: barW, h: bot - top, fill: { color: fill }, line: { type: "none" } });
    if (i < steps.length - 1) {
      // connector at the running level to the next bar
      s.addShape(pres.shapes.LINE, { objectName: `connector${i + 1}`, x: cx + barW / 2, y: yOf(to), w: colW - barW, h: 0, line: { color: C.accent4, width: 1, dashType: "dash" } });
    }
    const val = st.kind === "total" ? run : st.v;
    const vs = (val > 0 ? "＋" : "−") + Math.abs(val) + "万円";
    txt(s, `value${i + 1}`, vs, { x: cx - colW / 2, y: 4.95, w: colW, h: 0.5, fontSize: st.kind === "total" ? 22 : 20, bold: true, align: "center", valign: "middle",
      color: st.kind === "total" ? C.accent3 : st.kind === "up" ? C.text2 : C.text1 });
    txt(s, `cat${i + 1}`, st.label, { x: cx - colW / 2 + 0.05, y: 5.5, w: colW - 0.1, h: 0.75, fontSize: 15, align: "center", valign: "top", color: C.text1, bold: st.kind === "total" });
  });
  txt(s, "wf_note", "※説明用の例。他の入出金は省略。", { x: X0, y: 6.42, w: 6, h: 0.35, fontSize: 13, color: C.accent4 });
  card(s, "message_card", 9.35, 1.6, 3.38, 4.65, C.text2);
  txt(s, "message", [
    { text: "お金が消えた\nわけではない。", options: { fontSize: 28, bold: true, color: C.background1, breakLine: true } },
    { text: " ", options: { fontSize: 14, breakLine: true } },
    { text: "行き先が、\nある。", options: { fontSize: 36, bold: true, color: C.accent5 } },
  ], { x: 9.7, y: 1.6, w: 2.8, h: 4.65, valign: "middle", lineSpacingMultiple: 1.15 });
  notes(s, "2:00", "4:00",
`では、実際にどれくらいズレるのか。ひとつの例で、左から順番に見ていきます。

まず、税引後の利益が500万円出ました。ここまでは良い話です。
次に、減価償却費の100万円を足し戻します。減価償却費は、過去に買った設備の代金を何年かに分けて経費にしているもので、今年お金が出ていったわけではありません。だから通帳の目線では足し戻します。ここで600万円分です。

ところが、売掛金と在庫が合わせて300万円増えました。売ったけれどまだ回収していないお金と、倉庫に置いてある商品です。これで300万円。
さらに、借入金の元本の返済と設備の購入で、400万円を支払いました。
その結果、通帳は100万円減りました。利益は500万円なのに、通帳はマイナス100万円です。

ただ、ここで強調したいのは、お金が消えたわけではない、ということです。ちゃんと行き先があります。
なお、これは説明用に単純化した例で、ほかの入出金は省いています。`);

  // ================= Slide 4 =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "仕組み" });
  s.addText("お金の行き先は、大きく３つ", { placeholder: "title" });
  // source: bankbook
  const srcX = M, srcY = 2.45, srcW = 2.8, srcH = 3.0;
  card(s, "source_card", srcX, srcY, srcW, srcH, C.text2);
  s.addImage({ objectName: "source_icon", data: I.wallet, x: srcX + srcW / 2 - 0.45, y: srcY + 0.45, w: 0.9, h: 0.9, altText: "通帳のお金" });
  txt(s, "source_title", "通帳のお金", { x: srcX, y: srcY + 1.5, w: srcW, h: 0.6, fontSize: 26, bold: true, color: C.background1, align: "center" });
  txt(s, "source_sub", "利益で増えた分も\nここから移っていく", { x: srcX, y: srcY + 2.1, w: srcW, h: 0.7, fontSize: 15, color: C.background1, align: "center" });
  const dests = [
    { n: "①", icon: I.invoice, title: "まだ回収していない売上・在庫", where: "お金は今：取引先の手元と、倉庫の中", amt: "−300万円" },
    { n: "②", icon: I.bank, title: "借入金の返済", where: "お金は今：銀行へ。その分、借金が減った", amt: "−250万円" },
    { n: "③", icon: I.factory, title: "設備への投資", where: "お金は今：機械・車・システムに形を変えた", amt: "−150万円" },
  ];
  const dX = 4.6, dW = W - M - dX, dH = 1.3, dGap = 0.3, dY0 = 1.6;
  const srcRight = srcX + srcW, srcMid = srcY + srcH / 2;
  dests.forEach((d, i) => {
    const y = dY0 + i * (dH + dGap), mid = y + dH / 2;
    // arrow from source to card
    const ax = srcRight + 0.15, aw = dX - 0.15 - ax;
    const up = mid < srcMid;
    s.addShape(pres.shapes.LINE, { objectName: `flow${i + 1}`, x: ax, y: Math.min(mid, srcMid), w: aw, h: Math.abs(mid - srcMid), flipV: up,
      line: { color: C.accent2, width: 2.5, endArrowType: "triangle" } });
    card(s, `dest${i + 1}_card`, dX, y, dW, dH, C.background2);
    s.addShape(pres.shapes.OVAL, { objectName: `dest${i + 1}_iconbg`, x: dX + 0.3, y: y + 0.25, w: 0.8, h: 0.8, fill: { color: C.background1 }, line: { type: "none" } });
    s.addImage({ objectName: `dest${i + 1}_icon`, data: d.icon, x: dX + 0.48, y: y + 0.43, w: 0.44, h: 0.44, altText: d.title });
    txt(s, `dest${i + 1}_title`, d.n + " " + d.title, { x: dX + 1.35, y: y + 0.17, w: 4.7, h: 0.55, fontSize: 22, bold: true, color: C.text2, valign: "middle" });
    txt(s, `dest${i + 1}_where`, d.where, { x: dX + 1.35, y: y + 0.72, w: 4.7, h: 0.42, fontSize: 16, color: C.text1, valign: "middle" });
    txt(s, `dest${i + 1}_amt`, d.amt, { x: dX + dW - 2.25, y, w: 2.0, h: dH, fontSize: 26, bold: true, color: C.text1, align: "right", valign: "middle" });
  });
  txt(s, "dest_note", "※金額は前のスライドの例（説明用）。返済・設備購入の400万円を、返済250万円・設備150万円とした場合。", { x: M, y: 6.42, w: CW, h: 0.35, fontSize: 13, color: C.accent4 });
  notes(s, "1:30", "5:30",
`では、そのお金はどこへ行ったのか。大きく3つに分けられます。

1つ目は、まだ回収していない売上と在庫です。お金は今、取引先の手元と、倉庫の中にあります。いずれお金に戻る予定ですが、今は通帳にはありません。

2つ目は、借入金の返済です。お金は銀行に戻りましたが、その分、会社の借金は減っています。

3つ目は、設備への投資です。お金は機械や車、システムに形を変えて、会社の中に残っています。

先ほどの例でいえば、300万円が売掛金と在庫に、250万円が返済に、150万円が設備に移った、というイメージです。
どれも無駄遣いではありません。ただ、通帳から見えなくなっているだけなんです。`);

  // ================= Slide 5 =================
  pres.addSection({ title: "打ち手" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "打ち手" });
  s.addText("原因が違えば、打ち手も違う", { placeholder: "title" });
  const pairs = [
    { icon: I.invoice, cause: "売掛金が増える", act: "請求日・入金日・回収条件を確認", sub: "請求は遅れていないか／入金までの期間は長すぎないか" },
    { icon: I.boxes, cause: "在庫が増える", act: "売れ残りと発注量を確認", sub: "動いていない商品はないか／必要以上に発注していないか" },
    { icon: I.bank, cause: "返済・投資が重い", act: "時期と金額を、資金繰りに照らして確認", sub: "返済や投資の時期は、入金の見込みと合っているか" },
  ];
  const lX = M, lW = 4.2, aX = 5.0, aW = 0.7, rX = 5.9, rW = W - M - rX, rH = 1.3, rGap = 0.25, rY0 = 1.55;
  pairs.forEach((p, i) => {
    const y = rY0 + i * (rH + rGap);
    card(s, `cause${i + 1}_card`, lX, y, lW, rH, C.text2);
    s.addShape(pres.shapes.OVAL, { objectName: `cause${i + 1}_iconbg`, x: lX + 0.3, y: y + 0.25, w: 0.8, h: 0.8, fill: { color: C.background1 }, line: { type: "none" } });
    s.addImage({ objectName: `cause${i + 1}_icon`, data: p.icon, x: lX + 0.48, y: y + 0.43, w: 0.44, h: 0.44, altText: p.cause });
    txt(s, `cause${i + 1}_text`, p.cause, { x: lX + 1.3, y, w: lW - 1.45, h: rH, fontSize: 22, bold: true, color: C.background1, valign: "middle" });
    s.addShape(pres.shapes.RIGHT_ARROW, { objectName: `pair${i + 1}_arrow`, x: aX, y: y + rH / 2 - 0.25, w: aW, h: 0.5, fill: { color: C.accent2 }, line: { type: "none" } });
    card(s, `action${i + 1}_card`, rX, y, rW, rH, C.background2);
    txt(s, `action${i + 1}_text`, [
      { text: p.act, options: { fontSize: 22, bold: true, color: C.text2, breakLine: true } },
      { text: p.sub, options: { fontSize: 16, color: C.text1 } },
    ], { x: rX + 0.35, y, w: rW - 0.6, h: rH, valign: "middle", paraSpaceAfter: 4 });
  });
  txt(s, "invest_note", "設備投資も返済も、会社を強くするための大切なお金。見るべきは「時期」と「金額」のバランスです。", { x: M, y: 6.3, w: CW, h: 0.45, fontSize: 17, color: C.text2, bold: true, valign: "middle" });
  notes(s, "2:00", "7:30",
`行き先が分かれば、打つ手も見えてきます。ポイントは、原因が違えば、打ち手も違う、ということです。

まず、売掛金が増えている場合。請求日、入金日、回収の条件を確認します。請求書を出すのが遅れていないか、入金までの期間が長すぎないか。ここを整えるだけで、通帳の残り方が変わることがあります。

次に、在庫が増えている場合。売れ残っている商品と、発注の量を確認します。動いていない商品はないか、「念のため」の多めの発注が積み重なっていないか、を見ていきます。

そして、返済や投資が重い場合。ここは誤解のないようにお伝えしたいのですが、設備投資も返済も、会社を強くするための大切なお金です。悪いものではありません。
確認したいのは、その時期と金額が、資金繰りに合っているかどうか。入金の見込みと照らし合わせて、無理のない計画になっているかを見ます。

原因を確かめずに、とにかく経費を削る、というのは順番が逆なんですね。`);

  // ================= Slide 6 =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "打ち手" });
  s.addText("３か月先の通帳を予測する", { placeholder: "title" });
  // data (万円) and verification
  const months = ["1か月目", "2か月目", "3か月目"];
  const start0 = 800;
  const inflow = [1000, 950, 900], ops = [850, 900, 950], repay = [100, 100, 100], taxInv = [0, 300, 200];
  const begin = [], end = [];
  let bal = start0;
  for (let m = 0; m < 3; m++) { begin.push(bal); bal = bal + inflow[m] - ops[m] - repay[m] - taxInv[m]; end.push(bal); }
  const expectEnd = [850, 500, 150];
  if (end.join() !== expectEnd.join()) throw new Error("cash table mismatch " + end);
  for (let m = 1; m < 3; m++) if (begin[m] !== end[m - 1]) throw new Error("carry mismatch");
  const fmt = (n) => n.toLocaleString("en-US");
  const neg = (n) => (n === 0 ? "0" : "−" + fmt(n));
  txt(s, "formula", "月初の預金 ＋ 入金 − 仕入・人件費等 − 返済 − 税金・投資 ＝ 月末の預金", { x: M, y: 1.45, w: 8.2, h: 0.5, fontSize: 16, bold: true, color: C.text2, valign: "middle" });
  const hdr = { bold: true, color: C.background1, fill: { color: C.text2 }, align: "center", fontSize: 16 };
  const lab = { color: C.text1, fontSize: 17, align: "left" };
  const num = { color: C.text1, fontSize: 18, align: "right" };
  const rows = [
    [{ text: "（単位：万円）", options: { ...hdr, align: "left", fontSize: 13 } }, ...months.map((m) => ({ text: m, options: hdr }))],
    [{ text: "月初の預金", options: lab }, ...begin.map((v) => ({ text: fmt(v), options: num }))],
    [{ text: "＋ 入金", options: lab }, ...inflow.map((v) => ({ text: fmt(v), options: num }))],
    [{ text: "− 仕入・人件費等", options: lab }, ...ops.map((v) => ({ text: neg(v), options: num }))],
    [{ text: "− 返済", options: lab }, ...repay.map((v) => ({ text: neg(v), options: num }))],
    [{ text: "− 税金・投資", options: lab }, ...taxInv.map((v) => ({ text: neg(v), options: num }))],
    [{ text: "＝ 月末の預金", options: { ...lab, bold: true, fill: { color: C.background2 } } },
      ...end.map((v, m) => ({ text: fmt(v), options: { ...num, bold: true, fontSize: 20, fill: { color: C.background2 }, color: m === 2 ? C.accent3 : C.text2 } }))],
  ];
  s.addTable(rows, { objectName: "cash_table", x: M, y: 2.05, w: 8.2, colW: [2.95, 1.75, 1.75, 1.75], rowH: 0.47, border: { type: "solid", pt: 0.75, color: "C9D1DC" }, margin: [0, 0.15, 0, 0.15], valign: "middle" });
  txt(s, "table_note", "※説明用の架空の数字。2か月目：法人税等の納付　3か月目：設備の購入", { x: M, y: 5.45, w: 8.2, h: 0.35, fontSize: 13, color: C.accent4 });
  s.addChart(pres.charts.BAR, [{ name: "月末の預金", labels: months, values: end }], {
    objectName: "balance_chart", x: 9.2, y: 1.45, w: 3.53, h: 4.35, barDir: "col",
    showTitle: true, title: "月末の預金（万円）", titleFontSize: 15, titleColor: HEX.navy, titleFontFace: "+mn-lt",
    chartColors: [HEX.navy, HEX.navy, HEX.red], invertedColors: [HEX.navy, HEX.navy, HEX.red],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 16, dataLabelFontBold: true, dataLabelColor: HEX.ink, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: "#,##0",
    catAxisLabelColor: HEX.inkSoft, catAxisLabelFontSize: 13, catAxisLabelFontFace: "+mn-lt",
    valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 1000, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showLegend: false, barGapWidthPct: 60,
  });
  txt(s, "closing_line", "足りなくなる前に、手を打つ。", { x: M, y: 5.95, w: CW, h: 0.8, fontSize: 32, bold: true, color: C.text2, valign: "middle" });
  notes(s, "1:30", "9:00",
`最後に、これからの話です。おすすめしたいのは、3か月先の通帳を予測することです。

式はシンプルです。月初の預金に入金を足して、仕入や人件費、返済、税金や投資を引く。それが月末の預金です。

この表は説明用の架空の数字ですが、1か月目の月末は850万円残っています。ところが2か月目に法人税などの納付があって500万円、3か月目には設備の購入が重なって150万円まで減ります。右のグラフを見ると、減り方がよく分かりますね。

大事なのは、これが3か月前に分かっていれば、入金を早めてもらう相談をする、投資の時期をずらす、早めに銀行に相談する、といった手が打てることです。

足りなくなる前に、手を打つ。これが資金繰りの基本です。`);

  // ================= Slide 7 =================
  pres.addSection({ title: "まとめ" });
  s = pres.addSlide({ masterName: "CLOSING_DARK", sectionTitle: "まとめ" });
  s.addText("御社の利益は、どこへ行きましたか？", { placeholder: "title" });
  txt(s, "closing_msg", [
    { text: "決算書を見て終わりにせず、利益がお金として残る経営へ。", options: { fontSize: 24, bold: true, color: C.background1, breakLine: true } },
    { text: "自社の数字を使った『財務の作戦会議』で、お金の行き先と次の一手を一緒に整理します。", options: { fontSize: 19, color: C.background1 } },
  ], { x: M, y: 1.6, w: CW, h: 1.35, valign: "top", paraSpaceAfter: 10 });
  const cy = 3.25, ch = 3.0;
  card(s, "cta_card", M, cy, CW, ch, C.background1);
  txt(s, "cta_kicker", "個別相談", { x: M + 0.45, y: cy + 0.3, w: 3, h: 0.4, fontSize: 16, bold: true, color: C.accent2 });
  txt(s, "cta_title", "財務の作戦会議", { x: M + 0.45, y: cy + 0.7, w: 6, h: 0.7, fontSize: 32, bold: true, color: C.text2, valign: "middle" });
  const fields = [["お申込み", "（URLを入力）"], ["メール", "（メールアドレスを入力）"], ["電話", "（電話番号を入力）"]];
  fields.forEach(([k, v], i) => {
    const fy = cy + 1.55 + i * 0.45;
    txt(s, `cta_field${i + 1}_label`, k, { x: M + 0.45, y: fy, w: 1.3, h: 0.4, fontSize: 16, bold: true, color: C.text1, valign: "middle" });
    txt(s, `cta_field${i + 1}_value`, v, { x: M + 1.8, y: fy, w: 6.3, h: 0.4, fontSize: 16, color: C.accent6, valign: "middle" });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { objectName: "qr_box", x: M + CW - 2.75, y: cy + 0.35, w: 2.3, h: 2.3, rectRadius: 0.08, fill: { color: C.background1 }, line: { color: C.accent6, width: 1.5, dashType: "dash" } });
  txt(s, "qr_label", "QRコード\n貼り付け欄", { x: M + CW - 2.75, y: cy + 0.35, w: 2.3, h: 2.3, fontSize: 14, color: C.accent6, align: "center", valign: "middle" });
  txt(s, "speaker_end", "株式会社スフェノス　代表　小関 健太", { x: M, y: 6.45, w: 6, h: 0.35, fontSize: 15, color: C.background1 });
  txt(s, "reference", "参考：日本政策金融公庫「『黒字なのにお金がない』のはなぜ？」", { x: 6.4, y: 6.45, w: 5.6, h: 0.35, fontSize: 11, color: C.accent6, align: "right" });
  notes(s, "1:00", "10:00",
`では最後に、皆さんにお聞きします。御社の利益は、どこへ行きましたか？
（少し間を取る）
すぐに答えられなくても大丈夫です。

決算書を見て終わりにせず、利益がお金として残る経営へ。
そのために、自社の数字を使った「財務の作戦会議」という個別相談をご用意しています。御社のお金の行き先と、次の一手を一緒に整理します。

気になった方は、こちらからお気軽にお声がけください。本日はありがとうございました。

――――
参考資料：日本政策金融公庫「『黒字なのにお金がない』のはなぜ？」
https://www.jfc.go.jp/n/finance/keiei/support-plus/detail/materials.html?id=444`);

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  // 日本語フォントをテーマにも設定（見出し・本文とも游ゴシック）
  const JSZip = require("jszip");
  const fs = require("fs");
  const zip = await JSZip.loadAsync(fs.readFileSync(OUT), { createFolders: false });
  const tp = "ppt/theme/theme1.xml";
  let t = await zip.file(tp).async("string");
  t = t.replace(/<a:ea typeface=""\/>/g, '<a:ea typeface="Yu Gothic"/>').replace('typeface="游ゴシック Light"', 'typeface="游ゴシック"');
  zip.file(tp, t);
  fs.writeFileSync(OUT, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
  console.log("wrote", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
