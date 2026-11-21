// 「黒字なのに、お金が残らない会社の共通点」10分セミナー資料 生成スクリプト（v2：通帳の明細行モチーフ）
// 背景画像（assets/bg_title.jpg）は Codex CLI の画像生成で作成。
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const JSZip = require("jszip");
const fa = require("react-icons/fa6");
const { applyTheme } = require(process.env.PPTX_SKILL_SCRIPTS + "/apply_theme.js");

const OUT = process.argv[2] || "deck.pptx";
const ASSETS = process.argv[3] || path.join(__dirname, "assets");
const PHOTO = path.join(__dirname, "..", "assets", "koseki.jpg");
const BG = path.join(ASSETS, "bg_title.jpg");

const HEX = {
  ink: "26384A", navy: "16324F", white: "FFFFFF", tint: "EEF2F6",
  navyDeep: "0E2240", gold: "B08D3C", red: "A9342B", slate: "8795A5",
  goldBright: "C9A45C", coral: "E8907F", rule: "D5DCE4",
  seg1: "2E5A86", seg2: "5B7FA6", seg3: "8FA6C1",
};
const THEME = {
  name: "Sphenos Finance",
  headFontFace: "Yu Gothic",
  bodyFontFace: "Yu Gothic",
  colors: {
    dk1: HEX.ink, lt1: HEX.white, dk2: HEX.navy, lt2: HEX.tint,
    accent1: HEX.navyDeep, accent2: HEX.gold, accent3: HEX.red,
    accent4: HEX.slate, accent5: HEX.goldBright, accent6: HEX.coral,
    hlink: HEX.navy, folHlink: HEX.slate,
  },
};

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
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
  const bgData = "image/jpeg;base64," + fs.readFileSync(BG).toString("base64");

  // ---------- Layouts ----------
  pres.defineSlideMaster({
    title: "TITLE_DARK",
    background: { data: bgData },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 1.05, w: 7.6, h: 1.6, fontSize: 40, bold: true, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "subtitle", type: "body", x: 0.8, y: 2.8, w: 7.6, h: 0.5, fontSize: 24, bold: true, color: C.accent5, valign: "top", align: "left", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: C.background1 },
    objects: [
      { placeholder: { options: { name: "kicker", type: "body", x: M, y: 0.38, w: 6, h: 0.3, fontSize: 13, bold: true, color: C.accent2, valign: "middle", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: M, y: 0.68, w: 8.3, h: 0.75, fontSize: 32, bold: true, color: C.text2, valign: "middle", align: "left", margin: 0 }, text: "" } },
      { text: { text: "株式会社スフェノス｜黒字なのに、お金が残らない会社の共通点", options: { x: M, y: 6.98, w: 8, h: 0.3, fontSize: 11, color: C.accent4, margin: 0 } } },
    ],
    slideNumber: { x: 12.13, y: 6.98, w: 0.6, h: 0.3, fontSize: 11, color: C.accent4, align: "right", margin: 0 },
  });
  pres.defineSlideMaster({
    title: "CLOSING_DARK",
    background: { data: bgData },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: M, y: 0.55, w: 7.8, h: 1.45, fontSize: 40, bold: true, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
    ],
  });

  const shape = (s, type, name, o) => s.addShape(type, { objectName: name, line: { type: "none" }, ...o });
  const card = (s, name, x, y, w, h, fill) => shape(s, pres.shapes.ROUNDED_RECTANGLE, name, { x, y, w, h, rectRadius: 0.1, fill: { color: fill } });
  const txt = (s, name, text, o) => s.addText(text, { objectName: name, isTextBox: true, margin: 0, ...o });
  const rule = (s, name, x, y, w, color = HEX.rule, width = 1) => s.addShape(pres.shapes.LINE, { objectName: name, x, y, w, h: 0, line: { color, width } });
  const notes = (s, time, total, body) => s.addNotes(`【目安時間】${time}（累計 ${total}）\n\n${body}`);
  const imgData = (n) => "image/png;base64," + fs.readFileSync(path.join(ASSETS, n)).toString("base64");
  const IMG = { factory: imgData("case_factory.png"), receivable: imgData("dest_receivable.png"), bank: imgData("dest_bank.png"), machine: imgData("dest_machine.png") };
  // ケース企業（架空）：A社＝金属部品の加工、年商1.2億円、社員12名
  const caseBadge = (sl) => {
    const bx = 9.05, by = 0.38, bw = W - M - bx, bh2 = 1.05;
    card(sl, "case_badge", bx, by, bw, bh2, C.background2);
    shape(sl, pres.shapes.ROUNDED_RECTANGLE, "case_img_frame", { x: bx + 0.1, y: by + 0.1, w: 0.85, h: 0.85, rectRadius: 0.08, fill: { color: C.background1 } });
    sl.addImage({ objectName: "case_img", data: IMG.factory, x: bx + 0.12, y: by + 0.12, w: 0.81, h: 0.81, altText: "A社（金属部品の加工会社）のイラスト" });
    txt(sl, "case_text", [
      { text: "ケース：A社（架空）", options: { fontSize: 13, bold: true, color: C.accent2, breakLine: true } },
      { text: "金属部品の加工\n年商1.2億円・社員12名", options: { fontSize: 13, color: C.text1 } },
    ], { x: bx + 1.1, y: by + 0.08, w: bw - 1.2, h: bh2 - 0.16, valign: "middle", lineSpacingMultiple: 1.0 });
  };
  const content = (kicker, title, section, withCase = true) => {
    const sl = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
    sl.addText(kicker, { placeholder: "kicker" });
    sl.addText(title, { placeholder: "title" });
    if (withCase) caseBadge(sl);
    return sl;
  };

  const I = {
    wallet: await icon(fa.FaWallet, HEX.navy),
    invoice: await icon(fa.FaFileInvoice, HEX.navy),
    boxes: await icon(fa.FaBoxesStacked, HEX.navy),
    bank: await icon(fa.FaBuildingColumns, HEX.navy),
    factory: await icon(fa.FaIndustry, HEX.navy),
  };
  const iconDot = (s, name, data, x, y, d, fill = C.background2) => {
    shape(s, pres.shapes.OVAL, name + "_bg", { x, y, w: d, h: d, fill: { color: fill } });
    s.addImage({ objectName: name, data, x: x + d * 0.24, y: y + d * 0.24, w: d * 0.52, h: d * 0.52, altText: name });
  };
  const face = await sharp(PHOTO).extract({ left: 330, top: 20, width: 300, height: 300 }).resize(400, 400).jpeg({ quality: 88 }).toBuffer();
  const faceData = "image/jpeg;base64," + face.toString("base64");

  // ================= Slide 1 =================
  pres.addSection({ title: "導入" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "導入" });
  txt(s, "kicker", "経営者のための10分セミナー｜黒字なのに、お金が残らない会社の共通点", { x: 0.8, y: 0.55, w: 9, h: 0.35, fontSize: 14, color: C.accent5 });
  s.addText("黒字なのに、\nお金が残らないのはなぜ？", { placeholder: "title" });
  s.addText("利益500万円でも、通帳が100万円減る理由", { placeholder: "subtitle" });
  // ledger (通帳の明細行)
  const lx = 0.8, lw = 6.6, ly = 3.6, lh = 0.72;
  rule(s, "ledger_top", lx, ly, lw, "5A6F8C", 1);
  [["1年間の利益", "＋500万円", C.accent5], ["同じ1年の、通帳の増減", "−100万円", C.accent6]].forEach(([k, v, col], i) => {
    const y = ly + i * lh;
    txt(s, `ledger_label${i + 1}`, k, { x: lx, y, w: 3.6, h: lh, fontSize: 19, color: C.background1, valign: "middle" });
    txt(s, `ledger_value${i + 1}`, v, { x: lx + 3.0, y, w: lw - 3.0, h: lh, fontSize: 34, bold: true, color: col, align: "right", valign: "middle" });
    rule(s, `ledger_rule${i + 1}`, lx, y + lh, lw, "5A6F8C", 1);
  });
  txt(s, "question", "去年より利益が出たのに、通帳が増えていない。\nそんな経験はありませんか？", { x: 0.8, y: 5.25, w: 7.6, h: 0.85, fontSize: 20, color: C.background1, valign: "middle", lineSpacingMultiple: 1.15 });
  s.addImage({ objectName: "speaker_photo", data: faceData, x: 0.8, y: 6.35, w: 0.7, h: 0.7, rounding: true, altText: "講師 小関健太" });
  txt(s, "speaker", "株式会社スフェノス　代表　小関 健太", { x: 1.7, y: 6.35, w: 6.0, h: 0.7, fontSize: 16, color: C.background1, valign: "middle" });
  notes(s, "0:45", "0:45",
`皆さん、こんにちは。株式会社スフェノスの小関です。今日は10分だけ、会社のお金の話をさせてください。

まず、ひとつ質問です。
去年より利益が出たのに、通帳が増えていない。そんな経験はありませんか？
（少し間を取る）

実はこれ、珍しいことではありません。利益が500万円出ていても、通帳が100万円減る。こういうことは、普通に起こります。
今日はその理由と、自社ではどこを確認すればいいのかをお話しします。`);

  // ================= Slide 2 =================
  pres.addSection({ title: "仕組み" });
  s = content("01　なぜズレるのか", "利益と通帳残高は、動く時期が違う", "仕組み");
  const ex = [
    { n: "例1", scene: "A社が100万円分の部品を納品。\nでも、入金は来月", p: "＋100万円", c: "±0円",
      note: "※まだ入金されていない売上を「売掛金」といいます\n（説明のため、仕入などの経費は省略）" },
    { n: "例2", scene: "A社が銀行に、借入金の\n元本100万円を返した", p: "±0円", c: "−100万円",
      note: "※元本の返済は経費になりません\n（利息の部分は経費になります）" },
  ];
  ex.forEach((e, i) => {
    const w = 5.86, x = M + i * (w + 0.41), y = 1.75, h = 4.85, ix = x + 0.45, iw = w - 0.9;
    card(s, `ex${i + 1}_card`, x, y, w, h, C.background2);
    txt(s, `ex${i + 1}_tag`, e.n, { x: ix, y: y + 0.35, w: 1.5, h: 0.35, fontSize: 15, bold: true, color: C.accent2 });
    txt(s, `ex${i + 1}_scene`, e.scene, { x: ix, y: y + 0.7, w: iw, h: 1.0, fontSize: 24, bold: true, color: C.text2, valign: "top", lineSpacingMultiple: 1.05 });
    const ry = y + 2.0, rh = 0.9;
    rule(s, `ex${i + 1}_rule0`, ix, ry, iw, HEX.slate, 1);
    [["利益の計算", e.p, C.text2], ["今月の通帳", e.c, e.c.startsWith("−") ? C.accent3 : C.text2]].forEach(([lab, val, col], j) => {
      const yy = ry + j * rh;
      txt(s, `ex${i + 1}_row${j + 1}_label`, lab, { x: ix, y: yy, w: 2.2, h: rh, fontSize: 20, color: C.text1, valign: "middle" });
      txt(s, `ex${i + 1}_row${j + 1}_value`, val, { x: ix + 2.0, y: yy, w: iw - 2.0, h: rh, fontSize: 38, bold: true, color: col, align: "right", valign: "middle" });
      rule(s, `ex${i + 1}_rule${j + 1}`, ix, yy + rh, iw, HEX.slate, 1);
    });
    txt(s, `ex${i + 1}_note`, e.note, { x: ix, y: y + 3.9, w: iw, h: 0.75, fontSize: 16, color: C.text1, valign: "top" });
  });
  notes(s, "1:15", "2:00",
`最初に、いちばん大事なことをお伝えします。利益と通帳残高は、動く時期が違います。

ここからは、A社という会社を例にします。金属部品の加工をしている、年商1億2千万円、社員12名の会社です。架空の会社ですが、よくある姿です。

左の例です。A社が今月、100万円分の部品を納品しました。売上は今月の数字に入るので、利益の計算ではプラス100万円。でも、入金が来月なら、今月の通帳は1円も増えていません。

右の例は逆です。A社が銀行に、借入金の元本を100万円返しました。通帳からは100万円出ていきますが、元本の返済は経費になりません。だから利益は減らないんです。ちなみに、利息の部分は経費になります。

利益の計算と通帳は、別のタイミングで動いている。ここを押さえておいてください。`);

  // ================= Slide 3 (waterfall) =================
  s = content("02　A社の1年を数字で見る", "利益500万円でも、現金は100万円減る", "仕組み");
  const steps = [
    { label: "税引後利益", v: 500, kind: "up", d: "本業はしっかり黒字" },
    { label: "減価償却費の\n足し戻し", v: 100, kind: "up", d: "以前買った機械の経費分\n（今年の支払いはなし）" },
    { label: "売掛金・在庫\nの増加", v: -300, kind: "down", d: "大口先の入金は2か月後\n材料もまとめ買い" },
    { label: "借入元本の返済\n・設備購入", v: -400, kind: "down", d: "銀行へ返済250万円\n新しい機械150万円" },
    { label: "現金の増減", v: null, kind: "total", d: "通帳は1年で\n100万円減った" },
  ];
  const X0 = M, XW = CW, colW = XW / steps.length, barW = 1.35;
  const VMAX = 600, VMIN = -100, YT = 1.85, YB = 4.65, sc = (YB - YT) / (VMAX - VMIN);
  const yOf = (v) => YT + (VMAX - v) * sc;
  if (steps.filter((t) => t.v !== null).reduce((a, t) => a + t.v, 0) !== -100) throw new Error("waterfall total mismatch");
  rule(s, "zero_line", X0, yOf(0), XW, HEX.slate, 1);
  let run = 0;
  steps.forEach((st, i) => {
    const cx = X0 + i * colW + colW / 2;
    let from, to, fill;
    if (st.kind === "total") { from = 0; to = run; fill = C.accent3; }
    else { from = run; to = run + st.v; run = to; fill = st.kind === "up" ? C.text2 : C.accent4; }
    const top = yOf(Math.max(from, to)), bot = yOf(Math.min(from, to));
    shape(s, pres.shapes.RECTANGLE, `bar${i + 1}`, { x: cx - barW / 2, y: top, w: barW, h: bot - top, fill: { color: fill } });
    if (i < steps.length - 1)
      s.addShape(pres.shapes.LINE, { objectName: `connector${i + 1}`, x: cx + barW / 2, y: yOf(to), w: colW - barW, h: 0, line: { color: HEX.slate, width: 0.75, dashType: "dash" } });
    const val = st.kind === "total" ? run : st.v;
    txt(s, `value${i + 1}`, (val > 0 ? "＋" : "−") + Math.abs(val) + "万円", { x: cx - colW / 2, y: 4.8, w: colW, h: 0.55, fontSize: 28, bold: true, align: "center", valign: "middle",
      color: st.kind === "total" ? C.accent3 : st.kind === "up" ? C.text2 : C.text1 });
    txt(s, `cat${i + 1}`, st.label, { x: cx - colW / 2 + 0.05, y: 5.38, w: colW - 0.1, h: 0.62, fontSize: 17, align: "center", valign: "top", color: st.kind === "total" ? C.accent3 : C.text2, bold: true });
    txt(s, `detail${i + 1}`, st.d, { x: cx - colW / 2 + 0.05, y: 6.02, w: colW - 0.1, h: 0.55, fontSize: 14, align: "center", valign: "top", color: C.text1 });
  });
  txt(s, "message", [
    { text: "お金が消えたわけではない。", options: { fontSize: 24, bold: true, color: C.text2, breakLine: true } },
    { text: "行き先が、ある。", options: { fontSize: 38, bold: true, color: C.accent2 } },
  ], { x: X0 + 3 * colW + 0.15, y: 1.6, w: 2 * colW - 0.15, h: 1.2, valign: "top" });
  txt(s, "wf_note", "※説明用の例。他の入出金は省略。", { x: W - M - 5, y: 6.62, w: 5, h: 0.3, fontSize: 13, color: C.text1, align: "right" });
  notes(s, "2:00", "4:00",
`では、A社の1年を数字で見てみます。左から順番です。

まず、税引後の利益が500万円。本業はしっかり黒字です。
次に、減価償却費の100万円を足し戻します。以前買った機械の代金を、何年かに分けて経費にしている分で、今年お金は出ていません。ここで600万円分です。

ところが、大口の取引先が増えて、入金は2か月後。材料もまとめ買いしました。売掛金と在庫が合わせて300万円増えています。
さらに、銀行への返済が250万円、新しい機械の購入が150万円。合わせて400万円を支払いました。

その結果、A社の通帳は1年で100万円減りました。社長からすると「500万円も儲かったはずなのに、なぜ？」となるわけです。

でも、お金が消えたわけではありません。ちゃんと行き先があります。なお、これは説明用の例で、ほかの入出金は省いています。`);

  // ================= Slide 4 (proportional bars) =================
  s = content("03　A社のお金はどこへ移ったか", "お金の行き先は、大きく３つ", "仕組み");
  const BX = 3.2, BWID = 9.2, per = BWID / 700, bh = 0.62;
  const made = 600, dests = [
    { n: "①", v: 300, col: HEX.seg1, icon: I.invoice, title: "まだ回収していない\n売上・在庫", where: "お金は今：大口先の入金待ちと、\n倉庫に積んだ材料" },
    { n: "②", v: 250, col: HEX.seg2, icon: I.bank, title: "借入金の返済", where: "お金は今：銀行へ。\nその分、借入残高が減った" },
    { n: "③", v: 150, col: HEX.seg3, icon: I.factory, title: "設備への投資", where: "お金は今：新しい加工機械に\n形を変えた" },
  ];
  const destTotal = dests.reduce((a, d) => a + d.v, 0);
  if (destTotal - made !== 100) throw new Error("slide4 mismatch");
  const yA = 1.75, yB = 2.62;
  txt(s, "rowA_label", "利益＋減価償却費", { x: M, y: yA, w: 2.5, h: bh, fontSize: 18, bold: true, color: C.text2, valign: "middle" });
  shape(s, pres.shapes.RECTANGLE, "rowA_bar", { x: BX, y: yA, w: made * per, h: bh, fill: { color: C.text2 } });
  txt(s, "rowA_value", "600万円（税引後利益500＋減価償却費100）", { x: BX + 0.2, y: yA, w: made * per - 0.3, h: bh, fontSize: 18, bold: true, color: C.background1, valign: "middle" });
  txt(s, "rowB_label", "お金の行き先", { x: M, y: yB, w: 2.5, h: bh, fontSize: 18, bold: true, color: C.text2, valign: "middle" });
  let bx = BX;
  dests.forEach((d, i) => {
    const w = d.v * per;
    shape(s, pres.shapes.RECTANGLE, `rowB_seg${i + 1}`, { x: bx, y: yB, w: w - 0.03, h: bh, fill: { color: d.col } });
    txt(s, `rowB_seg${i + 1}_label`, `${d.n} ${d.v}万円`, { x: bx, y: yB, w: w - 0.03, h: bh, fontSize: 18, bold: true, color: i === 2 ? C.text2 : C.background1, align: "center", valign: "middle" });
    bx += w;
  });
  const overX = BX + made * per, overW = (destTotal - made) * per;
  s.addShape(pres.shapes.RECTANGLE, { objectName: "shortfall_slot", x: overX + 0.03, y: yA, w: overW - 0.06, h: bh, fill: { color: C.background1 }, line: { color: C.accent3, width: 1.5, dashType: "dash" } });
  txt(s, "shortfall_label", "不足\n−100万円", { x: overX, y: yA, w: overW, h: bh, fontSize: 13, bold: true, color: C.accent3, align: "center", valign: "middle", lineSpacingMultiple: 0.95 });
  txt(s, "shortfall_caption", "足りない100万円は、通帳から出ていった", { x: BX + BWID - 6, y: yB + bh + 0.08, w: 6, h: 0.38, fontSize: 16, bold: true, color: C.accent3, align: "right", valign: "middle" });
  const cy0 = 3.78, chh = 2.7, cw = (CW - 2 * 0.3) / 3;
  const destTitles = ["まだ回収していない\n売上・在庫", "借入金の返済", "設備への投資"];
  const destImgs = [IMG.receivable, IMG.bank, IMG.machine];
  for (let i = 0; i < dests.length; i++) {
    const d = dests[i], x = M + i * (cw + 0.3);
    card(s, `dest${i + 1}_card`, x, cy0, cw, chh, C.background2);
    shape(s, pres.shapes.ROUNDED_RECTANGLE, `dest${i + 1}_img_frame`, { x: x + 0.25, y: cy0 + 0.2, w: 1.05, h: 1.05, rectRadius: 0.08, fill: { color: C.background1 } });
    s.addImage({ objectName: `dest${i + 1}_img`, data: destImgs[i], x: x + 0.28, y: cy0 + 0.23, w: 0.99, h: 0.99, altText: d.title.replace("\n", "") });
    shape(s, pres.shapes.RECTANGLE, `dest${i + 1}_swatch`, { x: x + 1.5, y: cy0 + 0.58, w: 0.24, h: 0.24, fill: { color: d.col } });
    txt(s, `dest${i + 1}_amount`, `${d.n} ${d.v}万円`, { x: x + 1.85, y: cy0 + 0.4, w: cw - 2.0, h: 0.6, fontSize: 24, bold: true, color: C.text2, valign: "middle" });
    txt(s, `dest${i + 1}_title`, destTitles[i], { x: x + 0.3, y: cy0 + 1.35, w: cw - 0.5, h: 0.68, fontSize: 20, bold: true, color: C.text2, valign: "top" });
    txt(s, `dest${i + 1}_where`, d.where, { x: x + 0.3, y: cy0 + 2.05, w: cw - 0.45, h: 0.58, fontSize: 15, color: C.text1, valign: "top" });
  }
  txt(s, "dest_note", "※前のスライドの例。返済・設備購入の400万円を、返済250万円・設備150万円とした場合", { x: M, y: 6.55, w: CW, h: 0.35, fontSize: 14, color: C.text1 });
  notes(s, "1:30", "5:30",
`では、A社のお金はどこへ行ったのか。上の帯が、利益と減価償却費で生まれた600万円。下の帯がその行き先で、合計700万円です。はみ出した100万円が、通帳から出ていった分です。

1つ目は、まだ回収していない売上と在庫、300万円。大口先からの入金待ちと、倉庫に積んだ材料です。いずれお金に戻りますが、今は通帳にありません。

2つ目は、銀行への返済、250万円。その分、借入残高は減っています。

3つ目は、新しい加工機械、150万円。お金が機械に形を変えて、会社の中に残っています。

どれも無駄遣いではありません。通帳から見えなくなっているだけなんです。`);

  // ================= Slide 5 =================
  pres.addSection({ title: "打ち手" });
  s = content("04　A社なら、どこを確認するか", "原因が違えば、打ち手も違う", "打ち手");
  const pairs = [
    { icon: I.invoice, cause: "売掛金が増える", act: "請求日・入金日・回収条件を確認", sub: "大口先に、入金を早められないか相談する" },
    { icon: I.boxes, cause: "在庫が増える", act: "売れ残りと発注量を確認", sub: "材料のまとめ買いが、使う量より多くないか" },
    { icon: I.bank, cause: "返済・投資が重い", act: "時期と金額を、資金繰りに照らして確認", sub: "機械を買う月を、納税の月と重ねない" },
  ];
  txt(s, "head_cause", "原因", { x: M, y: 1.6, w: 3, h: 0.35, fontSize: 15, bold: true, color: C.accent2 });
  txt(s, "head_action", "確認すること", { x: 5.35, y: 1.6, w: 3, h: 0.35, fontSize: 15, bold: true, color: C.accent2 });
  const r0 = 2.0, rh5 = 1.3;
  rule(s, "pair_rule0", M, r0, CW, HEX.slate, 1);
  pairs.forEach((p, i) => {
    const y = r0 + i * rh5;
    iconDot(s, `cause${i + 1}_icon`, p.icon, M, y + (rh5 - 0.75) / 2, 0.75);
    txt(s, `cause${i + 1}_text`, p.cause, { x: M + 0.95, y, w: 3.3, h: rh5, fontSize: 24, bold: true, color: C.text2, valign: "middle" });
    shape(s, pres.shapes.RIGHT_ARROW, `pair${i + 1}_arrow`, { x: 4.55, y: y + rh5 / 2 - 0.17, w: 0.5, h: 0.34, fill: { color: C.accent2 } });
    txt(s, `action${i + 1}_text`, [
      { text: p.act, options: { fontSize: 24, bold: true, color: C.text1, breakLine: true } },
      { text: "A社なら　", options: { fontSize: 17, bold: true, color: C.accent2 } },
      { text: p.sub, options: { fontSize: 18, color: C.text1 } },
    ], { x: 5.35, y, w: W - M - 5.35, h: rh5, valign: "middle", paraSpaceAfter: 4 });
    rule(s, `pair_rule${i + 1}`, M, y + rh5, CW, HEX.rule, 1);
  });
  card(s, "invest_note_bg", M, 6.1, CW, 0.62, C.background2);
  txt(s, "invest_note", "設備投資も返済も、会社を強くする大切なお金。見るべきは「時期」と「金額」です。", { x: M + 0.35, y: 6.1, w: CW - 0.7, h: 0.62, fontSize: 18, bold: true, color: C.text2, valign: "middle" });
  notes(s, "2:00", "7:30",
`行き先が分かれば、打つ手も見えてきます。原因が違えば、打ち手も違います。

まず、売掛金が増えている場合。請求日、入金日、回収の条件を確認します。A社なら、大口の取引先に、入金を少し早められないか相談してみる。請求書を出すのが遅れていないかも見ます。

次に、在庫が増えている場合。売れ残りと発注量を確認します。A社なら、材料のまとめ買いが、実際に使う量より多くなっていないか、です。

そして、返済や投資が重い場合。ここは誤解のないようにお伝えしたいのですが、設備投資も返済も、会社を強くするための大切なお金です。悪いものではありません。
確認したいのは、時期と金額が資金繰りに合っているか。A社なら、機械を買う月を、納税の月と重ねないだけでも、通帳の山と谷はずいぶん変わります。

原因を確かめずに、とにかく経費を削る、というのは順番が逆なんですね。`);

  // ================= Slide 6 =================
  s = content("05　A社のこれからの通帳", "３か月先の通帳を予測する", "打ち手");
  const months = ["1か月目", "2か月目", "3か月目"];
  const inflow = [1000, 950, 900], ops = [850, 900, 950], repay = [100, 100, 100], taxInv = [0, 300, 200];
  const begin = [], end = [];
  let bal = 800;
  for (let m = 0; m < 3; m++) { begin.push(bal); bal = bal + inflow[m] - ops[m] - repay[m] - taxInv[m]; end.push(bal); }
  if (end.join() !== "850,500,150") throw new Error("cash table mismatch " + end);
  const fmt = (n) => n.toLocaleString("en-US");
  const neg = (n) => (n === 0 ? "0" : "−" + fmt(n));
  txt(s, "formula", "月初の預金 ＋ 入金 − 仕入・人件費等 − 返済 − 税金・投資 ＝ 月末の預金", { x: M, y: 1.6, w: 8.3, h: 0.4, fontSize: 16, bold: true, color: C.text2, valign: "middle" });
  const hdr = { bold: true, color: C.background1, fill: { color: C.text2 }, align: "right", fontSize: 17 };
  const lab = { color: C.text1, fontSize: 18, align: "left" };
  const num = { color: C.text1, fontSize: 20, align: "right" };
  const rows = [
    [{ text: "単位：万円", options: { ...hdr, align: "left", fontSize: 13, bold: false } }, ...months.map((m) => ({ text: m, options: hdr }))],
    [{ text: "月初の預金", options: lab }, ...begin.map((v) => ({ text: fmt(v), options: num }))],
    [{ text: "＋ 入金", options: lab }, ...inflow.map((v) => ({ text: fmt(v), options: num }))],
    [{ text: "− 仕入・人件費等", options: lab }, ...ops.map((v) => ({ text: neg(v), options: num }))],
    [{ text: "− 返済", options: lab }, ...repay.map((v) => ({ text: neg(v), options: num }))],
    [{ text: "− 税金・投資", options: lab }, ...taxInv.map((v) => ({ text: neg(v), options: num }))],
    [{ text: "＝ 月末の預金", options: { ...lab, bold: true, color: C.text2, fill: { color: C.background2 } } },
      ...end.map((v, m) => ({ text: fmt(v), options: { ...num, bold: true, fontSize: 22, fill: { color: C.background2 }, color: m === 2 ? C.accent3 : C.text2 } }))],
  ];
  s.addTable(rows, { objectName: "cash_table", x: M, y: 2.1, w: 8.3, colW: [2.9, 1.8, 1.8, 1.8], rowH: 0.47,
    border: [{ type: "none" }, { type: "none" }, { type: "solid", pt: 0.75, color: HEX.rule }, { type: "none" }], margin: [0, 0.18, 0, 0.18], valign: "middle" });
  txt(s, "table_note", "※A社の例（架空の数字）。2か月目：法人税等の納付　3か月目：機械の購入", { x: M, y: 5.45, w: 8.3, h: 0.4, fontSize: 15, color: C.text1 });
  s.addChart(pres.charts.BAR, [{ name: "月末の預金", labels: months, values: end }], {
    objectName: "balance_chart", x: 9.25, y: 1.6, w: 3.48, h: 4.2, barDir: "col",
    showTitle: true, title: "月末の預金（万円）", titleFontSize: 15, titleColor: HEX.navy, titleFontFace: "+mn-lt",
    chartColors: [HEX.navy, HEX.navy, HEX.red], invertedColors: [HEX.navy, HEX.navy, HEX.red],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 20, dataLabelFontBold: true, dataLabelColor: HEX.ink, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: "#,##0",
    catAxisLabelColor: HEX.ink, catAxisLabelFontSize: 14, catAxisLabelFontFace: "+mn-lt", catAxisLineShow: true,
    valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 1000, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showLegend: false, barGapWidthPct: 55,
  });
  txt(s, "closing_line", "足りなくなる前に、手を打つ。", { x: M, y: 5.95, w: CW, h: 0.8, fontSize: 32, bold: true, color: C.text2, valign: "middle" });
  notes(s, "1:30", "9:00",
`最後に、これからの話です。おすすめしたいのは、3か月先の通帳を予測することです。

式はシンプルです。月初の預金に入金を足して、仕入や人件費、返済、税金や投資を引く。それが月末の預金です。

これはA社の例です。1か月目の月末は850万円。ところが2か月目に法人税などの納付があって500万円、3か月目には機械の購入が重なって150万円まで減ります。右のグラフで、減り方がよく分かりますね。

これが3か月前に分かっていれば、入金を早めてもらう相談をする、機械の購入をずらす、早めに銀行に相談する、といった手が打てます。

足りなくなる前に、手を打つ。これが資金繰りの基本です。`);

  // ================= Slide 7 =================
  pres.addSection({ title: "まとめ" });
  s = pres.addSlide({ masterName: "CLOSING_DARK", sectionTitle: "まとめ" });
  s.addText("御社の利益は、\nどこへ行きましたか？", { placeholder: "title" });
  txt(s, "closing_msg", [
    { text: "決算書を見て終わりにせず、\n利益がお金として残る経営へ。", options: { fontSize: 22, bold: true, color: C.accent5, breakLine: true } },
    { text: "自社の数字を使った『財務の作戦会議』で、\nお金の行き先と次の一手を一緒に整理します。", options: { fontSize: 18, color: C.background1 } },
  ], { x: M, y: 2.25, w: 7.8, h: 1.75, valign: "top", paraSpaceAfter: 6, lineSpacingMultiple: 0.95 });
  const cx0 = M, cy = 4.3, cwid = 7.8, ch = 2.45;
  card(s, "cta_card", cx0, cy, cwid, ch, C.background1);
  txt(s, "cta_kicker", "個別相談", { x: cx0 + 0.4, y: cy + 0.25, w: 3, h: 0.32, fontSize: 15, bold: true, color: C.accent2 });
  txt(s, "cta_title", "財務の作戦会議", { x: cx0 + 0.4, y: cy + 0.55, w: 4.8, h: 0.6, fontSize: 30, bold: true, color: C.text2, valign: "middle" });
  // 連絡先はスフェノスHP（sphenos.com/contact/ の「会社のお金の健康診断・財務相談」フォーム）から転記
  const fields = [["お申込み", "sphenos.com/contact/"], ["メール", "info@sphenos.com"]];
  const fx = cx0 + 0.4, fw = 5.0, fy0 = cy + 1.3, fh = 0.48;
  fields.forEach(([k, v], i) => {
    const fy = fy0 + i * fh;
    txt(s, `cta_field${i + 1}_label`, k, { x: fx, y: fy, w: 1.2, h: fh, fontSize: 15, bold: true, color: C.text1, valign: "middle" });
    txt(s, `cta_field${i + 1}_value`, v, { x: fx + 1.25, y: fy, w: fw - 1.25, h: fh, fontSize: 19, bold: true, color: C.text2, valign: "middle" });
    rule(s, `cta_field${i + 1}_rule`, fx, fy + fh, fw, HEX.rule, 0.75);
  });
  const qrData = "image/png;base64," + fs.readFileSync(path.join(ASSETS, "qr_contact.png")).toString("base64");
  s.addImage({ objectName: "qr_code", data: qrData, x: cx0 + cwid - 2.05, y: cy + 0.2, w: 1.75, h: 1.75, altText: "お申込みページ（https://sphenos.com/contact/）のQRコード" });
  txt(s, "qr_label", "スマホで読み取り", { x: cx0 + cwid - 2.15, y: cy + 1.98, w: 1.95, h: 0.3, fontSize: 12, color: C.text1, align: "center", valign: "middle" });
  txt(s, "speaker_end", "株式会社スフェノス　代表　小関 健太", { x: M, y: 6.9, w: 6, h: 0.35, fontSize: 14, color: C.background1, valign: "middle" });
  txt(s, "reference", "参考：日本政策金融公庫「『黒字なのにお金がない』のはなぜ？」", { x: 6.3, y: 6.9, w: 6.43, h: 0.35, fontSize: 12, color: C.background2, align: "right", valign: "middle" });
  notes(s, "1:00", "10:00",
`では最後に、皆さんにお聞きします。御社の利益は、どこへ行きましたか？
（少し間を取る）
すぐに答えられなくても大丈夫です。

決算書を見て終わりにせず、利益がお金として残る経営へ。
そのために、自社の数字を使った「財務の作戦会議」という個別相談をご用意しています。御社のお金の行き先と、次の一手を一緒に整理します。

気になった方は、こちらのQRコードか、ホームページのお申し込みページから、お気軽にお申し込みください。本日はありがとうございました。

――――
参考資料：日本政策金融公庫「『黒字なのにお金がない』のはなぜ？」
https://www.jfc.go.jp/n/finance/keiei/support-plus/detail/materials.html?id=444`);

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  // 日本語フォントをテーマにも設定（見出し・本文とも游ゴシック）
  const zip = await JSZip.loadAsync(fs.readFileSync(OUT), { createFolders: false });
  const tp = "ppt/theme/theme1.xml";
  let t = await zip.file(tp).async("string");
  t = t.replace(/<a:ea typeface=""\/>/g, '<a:ea typeface="Yu Gothic"/>').replace('typeface="游ゴシック Light"', 'typeface="游ゴシック"');
  zip.file(tp, t);
  fs.writeFileSync(OUT, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
  console.log("wrote", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
