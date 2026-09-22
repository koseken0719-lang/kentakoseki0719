/**
 * NBF（商工会議所青年部 全国大会）動画からの誘導フォームを自動生成するスクリプト
 *
 * 使い方
 *  1. https://script.google.com/home/projects/create を開く（koseken0719@gmail.com でログイン）
 *  2. 既存のコードを全部消して、このファイルの中身をそのまま貼り付ける
 *  3. 関数 createNbfForm を選んで「実行」→ 初回のみ承認画面で許可
 *  4. 「実行ログ」に 編集用URL / 回答用URL / スプレッドシートURL が出力される
 *
 * 重要
 *  - 未確認事項（問い合わせ窓口・プライバシーポリシーURL 等）が残っているため、
 *    このスクリプトはフォームを「回答受付停止」の状態で作成します。
 *  - 本文中の【要確認】を実際の情報に差し替えてから、受付を開始してください。
 *  - テーマ色（ネイビー）はApps Scriptから設定できないため、作成後に手動で設定します（末尾の手順参照）。
 */

// ===== 差し替え箇所（確定したらここだけ書き換える）=========================
var CONTACT_DESK   = '【要確認：個人情報に関するお問い合わせ窓口（担当部署／メールアドレス／電話番号）】';
var PRIVACY_TREX   = '【要確認：株式会社TREX プライバシーポリシーURL】';
var PRIVACY_SPHENOS = '【要確認：株式会社スフェノス プライバシーポリシーURL】';
// =========================================================================

var FORM_TITLE = '電気料金の無料診断・利益改善のご相談';

var FORM_DESCRIPTION = [
  '毎月の電気料金に、見直しの余地があるか確認してみませんか。',
  '',
  'まずは下記よりお申し込みください。担当者から、電気明細の提出方法をご案内します。',
  '',
  '電気料金の診断は無料です。切替等のサービスをご利用いただく場合の条件は、別途ご説明します。',
  '',
  'ご希望の方には、株式会社スフェノスによる販管費全体の見直し相談もご案内します。こちらの相談内容・費用は事前にご案内します。',
  '',
  'このフォームでは、電気明細や決算書の添付は不要です。'
].join('\n');

var CONFIRMATION_MESSAGE = [
  'お申し込みありがとうございます。',
  '',
  'ご入力いただいた連絡先へ、担当者からご連絡します。',
  '',
  '電気料金の無料診断をご希望の方には、電気明細の提出方法をご案内します。',
  '',
  '販管費全体の見直し相談をご希望の方には、相談の進め方と費用を事前にご案内します。',
  '',
  '森瀬会長へ直接ご相談いただくこともできます。'
].join('\n');

var CHOICE_1 = '電気料金の無料診断を希望する';
var CHOICE_2 = '電気料金の無料診断と、販管費全体の見直し相談を希望する';
var CHOICE_3 = 'まずはサービスの説明を聞きたい';

var PRIVACY_TEXT = [
  '■ 受付・管理主体',
  '本フォームの回答は、株式会社TREX（東京都渋谷区渋谷2-3-4 スタービル青山3階／代表取締役 森山佳樹）が受け付け、管理します。',
  '',
  '■ 利用目的',
  '(1) 本申込みへの対応およびご連絡',
  '(2) 電気料金の無料診断に必要な資料（電気明細）の提出方法のご案内',
  '(3) ご希望いただいたサービスに関するご連絡・ご提案',
  '上記以外の目的には利用しません。メールマガジンの配信や、ご希望のないサービスのご案内には利用しません。',
  '',
  '■ 第三者への提供',
  '上記「ご希望の内容」で②「' + CHOICE_2 + '」を選択された方についてのみ、販管費全体の見直し相談を担当する株式会社スフェノスへ、本フォームにご入力いただいた内容（会社名・屋号、お名前、所属する商工会議所・青年部など、メールアドレス、電話番号、ご希望の内容、ご質問・連絡事項）を提供します。提供の目的は、販管費全体の見直し相談に関するご連絡・ご提案です。',
  '①または③を選択された方の情報は、株式会社スフェノスへ提供しません。',
  '※ 株式会社TREXと株式会社スフェノスは別の法人です。電気料金の診断は株式会社TREX、販管費全体の見直し・財務コンサルティングは株式会社スフェノスが担当します。',
  '',
  '■ 個人情報に関するお問い合わせ窓口',
  CONTACT_DESK,
  '',
  '■ プライバシーポリシー',
  '株式会社TREX：' + PRIVACY_TREX,
  '株式会社スフェノス：' + PRIVACY_SPHENOS
].join('\n');


function createNbfForm() {
  var form = FormApp.create(FORM_TITLE);
  form.setTitle(FORM_TITLE);
  form.setDescription(FORM_DESCRIPTION);

  // --- Q1 会社名・屋号（記述式・短文・必須）
  form.addTextItem()
      .setTitle('会社名・屋号')
      .setRequired(true);

  // --- Q2 お名前（記述式・短文・必須）
  form.addTextItem()
      .setTitle('お名前')
      .setRequired(true);

  // --- Q3 所属する商工会議所・青年部など（記述式・短文・任意）
  form.addTextItem()
      .setTitle('所属する商工会議所・青年部など')
      .setRequired(false);

  // --- Q4 メールアドレス（記述式・短文・必須・形式チェックあり）
  var emailItem = form.addTextItem()
      .setTitle('メールアドレス')
      .setRequired(true);
  emailItem.setValidation(
    FormApp.createTextValidation()
      .setHelpText('メールアドレスの形式でご入力ください。')
      .requireTextIsEmail()
      .build()
  );

  // --- Q5 電話番号（記述式・短文・任意・形式チェックなし）
  form.addTextItem()
      .setTitle('電話番号')
      .setHelpText('お電話での連絡をご希望の場合はご記入ください。')
      .setRequired(false);

  // --- Q6 ご希望の内容（ラジオボタン・単一選択・必須・事前選択なし）
  form.addMultipleChoiceItem()
      .setTitle('ご希望の内容')
      .setHelpText('販管費全体の見直し相談は、株式会社スフェノスが担当します。相談内容・費用は事前にご案内します。')
      .setChoiceValues([CHOICE_1, CHOICE_2, CHOICE_3])
      .showOtherOption(false)
      .setRequired(true);

  // --- Q7 ご質問・連絡事項（記述式・長文・任意）
  form.addParagraphTextItem()
      .setTitle('ご質問・連絡事項')
      .setHelpText('ご質問や、ご希望の連絡時間帯などがあればご記入ください。決算情報などの詳細は、ここには記載不要です。')
      .setRequired(false);

  // --- 個人情報の取り扱い（本文表示。ページは分けない）
  form.addSectionHeaderItem()
      .setTitle('個人情報の取り扱い')
      .setHelpText(PRIVACY_TEXT);

  // --- Q8 同意（チェックボックス・必須・事前チェックなし）
  form.addCheckboxItem()
      .setTitle('個人情報の取り扱いへの同意')
      .setChoiceValues(['下記の個人情報の取り扱いに同意する'])
      .showOtherOption(false)
      .setRequired(true);

  // ===== フォーム設定 =====
  form.setCollectEmail(false);          // Googleアカウントからメールを自動収集しない＝本人が入力
  form.setLimitOneResponsePerUser(false); // 回答を1回に制限しない
  form.setAllowResponseEdits(false);
  form.setPublishingSummary(false);     // 回答の概要を回答者に公開しない
  form.setShuffleQuestions(false);      // 質問をシャッフルしない
  form.setIsQuiz(false);                // クイズ形式にしない
  form.setProgressBar(false);           // 1ページ構成なので進行状況バーなし
  form.setShowLinkToRespondAgain(false);
  form.setConfirmationMessage(CONFIRMATION_MESSAGE);

  // 組織内限定を解除（個人アカウントでは設定不可のため例外を無視）
  try {
    form.setRequireLogin(false);
  } catch (e) {
    Logger.log('setRequireLogin は個人アカウントでは設定不要／不可です: ' + e.message);
  }

  // ===== 回答先スプレッドシートを新規作成して連携 =====
  var ss = SpreadsheetApp.create('NBF_電気料金無料診断_申込管理');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  // ===== 未確認事項が残っているため、回答受付は停止した状態で保存 =====
  form.setAcceptingResponses(false);

  var out = [
    '',
    '================ 作成結果 ================',
    '編集用URL          : ' + form.getEditUrl(),
    '回答用URL          : ' + form.getPublishedUrl(),
    '回答用URL（短縮）  : ' + form.shortenFormUrl(form.getPublishedUrl()),
    'スプレッドシートURL: ' + ss.getUrl(),
    '回答受付           : 停止（未確認事項の差し替え後に開始してください）',
    '=========================================',
    ''
  ].join('\n');
  Logger.log(out);
  return out;
}

/**
 * 未確認事項を差し替えたあとに実行すると、回答受付を開始します。
 * 引数に編集用URLではなくフォームIDを渡してください（編集用URLの /d/ と /edit の間の文字列）。
 */
function startAcceptingResponses(formId) {
  var form = FormApp.openById(formId);
  form.setAcceptingResponses(true);
  Logger.log('回答受付を開始しました: ' + form.getPublishedUrl());
}

/*
 * ===== 作成後に手動で行う設定（Apps Scriptからは変更できません）=====
 *
 * デザイン（ネイビー基調／白背景）
 *   フォーム編集画面 右上のパレットアイコン →
 *     ・テーマの色  : カスタム → 1B2A4A（ネイビー）
 *     ・背景色      : 白（最も明るいもの）
 *     ・フォント    : 基本
 *   ヘッダー画像は設定しません（提供されたロゴがないため、架空のロゴは作成していません）。
 */
