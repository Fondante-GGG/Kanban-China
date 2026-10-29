import { LanguageCode } from '@/types';

export interface Translations {
  appName: string;
  board: string;
  reports: string;
  admin: string;
  login: string;
  logout: string;
  switchAccount: string;
  demoAccounts: string;
  theme: string;
  language: string;
  searchPlaceholder: string;
  allPriorities: string;
  priorityLow: string;
  priorityMedium: string;
  priorityHigh: string;
  priorityUrgent: string;
  allAssignees: string;
  addCard: string;
  addColumn: string;
  renameColumn: string;
  deleteColumn: string;
  editCard: string;
  deleteCard: string;
  cardTitle: string;
  cardDescription: string;
  priority: string;
  dueDate: string;
  assignees: string;
  checklists: string;
  addChecklistItem: string;
  attachments: string;
  uploadFile: string;
  comments: string;
  addComment: string;
  activityHistory: string;
  showOriginal: string;
  showingOriginal: string;
  save: string;
  cancel: string;
  delete: string;
  confirmDelete: string;
  overdue: string;
  completed: string;
  inProgress: string;
  bugs: string;
  total: string;
  successRate: string;
  week: string;
  month: string;
  quarter: string;
  exportExcel: string;
  exportWord: string;
  exportPdf: string;
  departmentReport: string;
  employeeReport: string;
  avgCompletionHours: string;
  roleDirector: string;
  roleManager: string;
  roleEmployee: string;
  usersManagement: string;
  boardsManagement: string;
  addUser: string;
  addBoard: string;
  fullName: string;
  email: string;
  phone: string;
  role: string;
  department: string;
  assignedBoard: string;
  status: string;
  active: string;
  blocked: string;
  password: string;
  resetPassword: string;
  notifications: string;
  noNotifications: string;
  markAllRead: string;
  noCardsYet: string;
  noBoardsFound: string;
  changeBackground: string;
  selectLanguageVariant: string;

  // Attendance & Time Tracking
  attendance: string;
  checkIn: string;
  checkOut: string;
  leaveBreak: string;
  resumeBreak: string;
  inOffice: string;
  outsideOffice: string;
  onBreak: string;
  notCheckedIn: string;
  timesheet: string;
  myAttendance: string;
  teamTimesheet: string;
  officesAndSchedules: string;
  lateArrivals: string;
  earlyDepartures: string;
  workedHours: string;
  vacation: string;
  sickLeave: string;
  businessTrip: string;
  dayOff: string;
  lunch: string;
  businessBreak: string;
  personalBreak: string;
  otherBreak: string;
  editRecord: string;
  mandatoryReason: string;
  locationConsent: string;
  consentGranted: string;
  grantConsent: string;
  revokeConsent: string;
  radiusMeters: string;
}

export const translations: Record<LanguageCode, Translations> = {
  ru: {
    appName: "Yrys Kanban",
    board: "Канбан-доска",
    reports: "Отчёты и аналитика",
    admin: "Администрирование",
    login: "Войти",
    logout: "Выйти",
    switchAccount: "Быстрое переключение аккаунта",
    demoAccounts: "Тестовые профили",
    theme: "Тема",
    language: "Язык",
    searchPlaceholder: "Поиск задач по названию и описанию...",
    allPriorities: "Все приоритеты",
    priorityLow: "Низкий",
    priorityMedium: "Средний",
    priorityHigh: "Высокий",
    priorityUrgent: "Срочный",
    allAssignees: "Все исполнители",
    addCard: "Добавить карточку",
    addColumn: "Новый раздел",
    renameColumn: "Переименовать",
    deleteColumn: "Удалить раздел",
    editCard: "Редактировать задачу",
    deleteCard: "Удалить карточку",
    cardTitle: "Название задачи",
    cardDescription: "Подробное описание",
    priority: "Приоритет",
    dueDate: "Срок выполнения",
    assignees: "Исполнители",
    checklists: "Чек-лист",
    addChecklistItem: "Добавить пункт...",
    attachments: "Вложения и файлы",
    uploadFile: "Загрузить файл",
    comments: "Комментарии",
    addComment: "Написать комментарий...",
    activityHistory: "История изменений",
    showOriginal: "Показать оригинал",
    showingOriginal: "Показан оригинал",
    save: "Сохранить",
    cancel: "Отмена",
    delete: "Удалить",
    confirmDelete: "Вы уверены, что хотите удалить?",
    overdue: "Просрочено",
    completed: "Выполнено",
    inProgress: "В процессе",
    bugs: "Баги",
    total: "Всего задач",
    successRate: "Успешность",
    week: "Неделя",
    month: "Месяц",
    quarter: "Квартал",
    exportExcel: "Выгрузить в Excel (.xlsx)",
    exportWord: "Выгрузить в Word (.docx)",
    exportPdf: "Выгрузить в PDF (.pdf)",
    departmentReport: "Показатели по отделам",
    employeeReport: "Показатели по сотрудникам",
    avgCompletionHours: "Ср. время выполнения",
    roleDirector: "Генеральный директор",
    roleManager: "Руководитель",
    roleEmployee: "Сотрудник",
    usersManagement: "Пользователи системы",
    boardsManagement: "Канбан-доски отделов",
    addUser: "Новый пользователь",
    addBoard: "Создать доску",
    fullName: "ФИО",
    email: "Email / Логин",
    phone: "Телефон",
    role: "Роль в системе",
    department: "Отдел",
    assignedBoard: "Привязанная доска (только одна)",
    status: "Статус",
    active: "Активен",
    blocked: "Заблокирован",
    password: "Пароль",
    resetPassword: "Сбросить пароль",
    notifications: "Уведомления",
    noNotifications: "Новых уведомлений нет",
    markAllRead: "Прочитать все",
    noCardsYet: "В этом разделе ещё нет задач",
    noBoardsFound: "Нет доступных досок",
    changeBackground: "Цвет фона",
    selectLanguageVariant: "Вариант китайского языка",
    attendance: "Учёт времени",
    checkIn: "Пришёл",
    checkOut: "Ушёл",
    leaveBreak: "Отлучился",
    resumeBreak: "Вернулся",
    inOffice: "В офисе",
    outsideOffice: "Вне офиса",
    onBreak: "На перерыве",
    notCheckedIn: "Не на смене",
    timesheet: "Табель",
    myAttendance: "Мои отметки",
    teamTimesheet: "Табель сотрудников",
    officesAndSchedules: "Офисы и графики",
    lateArrivals: "Опоздания",
    earlyDepartures: "Ранние уходы",
    workedHours: "Отработано часов",
    vacation: "Отпуск",
    sickLeave: "Больничный",
    businessTrip: "Командировка",
    dayOff: "Выходной",
    lunch: "Обед",
    businessBreak: "По делам компании",
    personalBreak: "Личное",
    otherBreak: "Другое",
    editRecord: "Исправить отметку",
    mandatoryReason: "Обязательная причина правки",
    locationConsent: "Согласие на отслеживание геопозиции",
    consentGranted: "Согласие предоставлено",
    grantConsent: "Дать согласие",
    revokeConsent: "Отозвать согласие",
    radiusMeters: "Радиус (м)",
  },
  'zh-Hans': {
    appName: "Yrys 看板系统",
    board: "任务看板",
    reports: "统计与报表",
    admin: "系统管理",
    login: "登录",
    logout: "退出登录",
    switchAccount: "快速切换测试账号",
    demoAccounts: "演示角色",
    theme: "界面主题",
    language: "语言选择",
    searchPlaceholder: "按标题或描述快速搜索卡片...",
    allPriorities: "所有优先级",
    priorityLow: "低优先级",
    priorityMedium: "中等",
    priorityHigh: "高优先级",
    priorityUrgent: "极其紧急",
    allAssignees: "所有执行人",
    addCard: "添加卡片",
    addColumn: "新建分组列",
    renameColumn: "重命名列",
    deleteColumn: "删除此列",
    editCard: "编辑任务",
    deleteCard: "删除任务卡片",
    cardTitle: "任务标题",
    cardDescription: "详细说明",
    priority: "优先级",
    dueDate: "截止日期",
    assignees: "负责人",
    checklists: "子任务检查清单",
    addChecklistItem: "添加检查项...",
    attachments: "附件与文件",
    uploadFile: "上传新文件",
    comments: "讨论留言",
    addComment: "发表评论留言...",
    activityHistory: "操作变更日志",
    showOriginal: "显示原文",
    showingOriginal: "当前显示原文",
    save: "保存更改",
    cancel: "取消",
    delete: "删除",
    confirmDelete: "确定要执行删除操作吗？",
    overdue: "已逾期",
    completed: "已完成",
    inProgress: "进行中",
    bugs: "缺陷/故障",
    total: "任务总数",
    successRate: "达成完成率",
    week: "最近一周",
    month: "最近一月",
    quarter: "最近一季",
    exportExcel: "导出 Excel 表格 (.xlsx)",
    exportWord: "导出 Word 文档 (.docx)",
    exportPdf: "导出 PDF 报表 (.pdf)",
    departmentReport: "各部门效能指标",
    employeeReport: "员工绩效考核清单",
    avgCompletionHours: "平均处理用时",
    roleDirector: "总经理",
    roleManager: "部门主管",
    roleEmployee: "普通员工",
    usersManagement: "组织成员管理",
    boardsManagement: "部门看板管理",
    addUser: "创建新成员",
    addBoard: "创建新看板",
    fullName: "姓名",
    email: "登录邮箱",
    phone: "联系电话",
    role: "系统角色",
    department: "所属部门",
    assignedBoard: "关联业务看板（仅限一个）",
    status: "账户状态",
    active: "正常启用",
    blocked: "已冻结停用",
    password: "登录密码",
    resetPassword: "重置密码",
    notifications: "系统通知",
    noNotifications: "暂无未读消息",
    markAllRead: "全部标为已读",
    noCardsYet: "此栏目暂无任务卡片",
    noBoardsFound: "暂无被授权的看板",
    changeBackground: "更换看板背景",
    selectLanguageVariant: "选择中文版本",
    attendance: "考勤与工时",
    checkIn: "签到 (上班)",
    checkOut: "签退 (下班)",
    leaveBreak: "暂离/外出",
    resumeBreak: "返回工位",
    inOffice: "在办公室",
    outsideOffice: "超出办公区",
    onBreak: "暂离休整中",
    notCheckedIn: "尚未签到",
    timesheet: "考勤工时表",
    myAttendance: "我的打卡记录",
    teamTimesheet: "部门员工考勤表",
    officesAndSchedules: "办公区与排班",
    lateArrivals: "迟到",
    earlyDepartures: "早退",
    workedHours: "实计工时",
    vacation: "年假",
    sickLeave: "病假",
    businessTrip: "出差",
    dayOff: "休息日",
    lunch: "午休就餐",
    businessBreak: "公事外出",
    personalBreak: "私事外出",
    otherBreak: "其他事由",
    editRecord: "更正打卡时间",
    mandatoryReason: "请填写修改原因（必填）",
    locationConsent: "工作时间位置授权协议",
    consentGranted: "已授权位置跟踪",
    grantConsent: "签署同意书",
    revokeConsent: "撤回授权",
    radiusMeters: "有效半径 (米)",
  },
  'zh-Hant': {
    appName: "Yrys 看板系統",
    board: "任務看板",
    reports: "統計與報表",
    admin: "系統管理",
    login: "登入",
    logout: "登出系統",
    switchAccount: "快速切換測試帳號",
    demoAccounts: "展示身分",
    theme: "外觀佈景",
    language: "系統語系",
    searchPlaceholder: "按標題或描述快速搜尋卡片...",
    allPriorities: "所有優先級",
    priorityLow: "低優先級",
    priorityMedium: "普通",
    priorityHigh: "高優先級",
    priorityUrgent: "緊急處理",
    allAssignees: "所有執行者",
    addCard: "新增卡片",
    addColumn: "新增分組欄",
    renameColumn: "重新命名",
    deleteColumn: "刪除此欄位",
    editCard: "編輯任務內容",
    deleteCard: "刪除任務卡片",
    cardTitle: "任務主旨",
    cardDescription: "詳細說明",
    priority: "優先層級",
    dueDate: "截止期限",
    assignees: "承辦同仁",
    checklists: "檢核清單",
    addChecklistItem: "新增待檢項目...",
    attachments: "隨附檔案",
    uploadFile: "上傳附件",
    comments: "討論留言",
    addComment: "發表備註評論...",
    activityHistory: "變更歷史軌跡",
    showOriginal: "檢視原文",
    showingOriginal: "目前檢視為原文",
    save: "確認儲存",
    cancel: "取消動作",
    delete: "確認刪除",
    confirmDelete: "確定要刪除此項目嗎？",
    overdue: "逾期未完",
    completed: "已結案完成",
    inProgress: "處理進行中",
    bugs: "問題缺失",
    total: "任務總計",
    successRate: "達成率",
    week: "最近一週",
    month: "最近一月",
    quarter: "最近一季",
    exportExcel: "匯出 Excel 活頁簿 (.xlsx)",
    exportWord: "匯出 Word 文件 (.docx)",
    exportPdf: "匯出 PDF 檔案 (.pdf)",
    departmentReport: "各部門效能報告",
    employeeReport: "同仁個人績效報表",
    avgCompletionHours: "平均耗時",
    roleDirector: "總經理",
    roleManager: "部門主管",
    roleEmployee: "專案成員",
    usersManagement: "人員權限維護",
    boardsManagement: "工作看板維護",
    addUser: "建立新使用者",
    addBoard: "開立新看板",
    fullName: "姓名",
    email: "電子郵箱",
    phone: "聯絡電話",
    role: "系統權限",
    department: "服務部門",
    assignedBoard: "所屬負責看板（限單一）",
    status: "帳號狀態",
    active: "正常運作",
    blocked: "已鎖定停權",
    password: "登入密碼",
    resetPassword: "變更密碼",
    notifications: "提醒通知",
    noNotifications: "目前無未讀通知",
    markAllRead: "標示全已讀取",
    noCardsYet: "此欄目尚未建立卡片",
    noBoardsFound: "目前尚無授權看板",
    changeBackground: "調整底色主題",
    selectLanguageVariant: "中文切換選項",
    attendance: "考勤與工時",
    checkIn: "簽到 (上班)",
    checkOut: "簽退 (下班)",
    leaveBreak: "暫離/外出",
    resumeBreak: "返回工位",
    inOffice: "在辦公室",
    outsideOffice: "超出辦公區",
    onBreak: "暫離休整中",
    notCheckedIn: "尚未簽到",
    timesheet: "考勤工時表",
    myAttendance: "我的打卡記錄",
    teamTimesheet: "部門員工考勤表",
    officesAndSchedules: "辦公區與排班",
    lateArrivals: "遲到",
    earlyDepartures: "早退",
    workedHours: "實計工時",
    vacation: "年假",
    sickLeave: "病假",
    businessTrip: "出差",
    dayOff: "休息日",
    lunch: "午休就餐",
    businessBreak: "公事外出",
    personalBreak: "私事外出",
    otherBreak: "其他事由",
    editRecord: "更正打卡時間",
    mandatoryReason: "請填寫修改原因（必填）",
    locationConsent: "工作時間位置授權協議",
    consentGranted: "已授權位置跟蹤",
    grantConsent: "簽署同意書",
    revokeConsent: "撤回授權",
    radiusMeters: "有效半徑 (公尺)",
  },
  ky: {
    appName: "Yrys Канбан",
    board: "Канбан тактасы",
    reports: "Отчеттор жана статистика",
    admin: "Администрациялоо",
    login: "Кирүү",
    logout: "Чыгуу",
    switchAccount: "Аккаунтту тез алмаштыруу",
    demoAccounts: "Тесттик колдонуучулар",
    theme: "Темасы",
    language: "Тил тандоо",
    searchPlaceholder: "Тапшырмаларды аты жана баяндамасы боюнча издөө...",
    allPriorities: "Бардык артыкчылыктар",
    priorityLow: "Төмөн",
    priorityMedium: "Орточо",
    priorityHigh: "Жогору",
    priorityUrgent: "Шашылыш",
    allAssignees: "Бардык аткаруучулар",
    addCard: "Тапшырма кошуу",
    addColumn: "Жаңы тилке",
    renameColumn: "Атын өзгөртүү",
    deleteColumn: "Тилкени өчүрүү",
    editCard: "Тапшырманы өзгөртүү",
    deleteCard: "Карточканы өчүрүү",
    cardTitle: "Тапшырманын аталышы",
    cardDescription: "Толук баяндамасы",
    priority: "Артыкчылыгы",
    dueDate: "Аткаруу мөөнөтү",
    assignees: "Аткаруучулар",
    checklists: "Чек-тизме",
    addChecklistItem: "Пункт кошуу...",
    attachments: "Тиркелген файлдар",
    uploadFile: "Файл жүктөө",
    comments: "Комментарийлер",
    addComment: "Комментарий жазуу...",
    activityHistory: "Өзгөртүүлөр тарыхы",
    showOriginal: "Түп нускасын көрсөтүү",
    showingOriginal: "Түп нускасы көрсөтүлүүдө",
    save: "Сактоо",
    cancel: "Жокко чыгаруу",
    delete: "Өчүрүү",
    confirmDelete: "Өчүрүүгө ишенесизби?",
    overdue: "Мөөнөтү өткөн",
    completed: "Аткарылды",
    inProgress: "Аткарылууда",
    bugs: "Мүчүлүштүктөр",
    total: "Бардык тапшырмалар",
    successRate: "Ийгиликтүүлүк",
    week: "Жума",
    month: "Ай",
    quarter: "Квартал",
    exportExcel: "Excel форматында жүктөө (.xlsx)",
    exportWord: "Word форматында жүктөө (.docx)",
    exportPdf: "PDF форматында жүктөө (.pdf)",
    departmentReport: "Бөлүмдөр боюнча көрсөткүчтөр",
    employeeReport: "Кызматкерлер боюнча көрсөткүчтөр",
    avgCompletionHours: "Орточо аткаруу убактысы",
    roleDirector: "Башкы директор",
    roleManager: "Жетекчи",
    roleEmployee: "Кызматкер",
    usersManagement: "Колдонуучуларды башкаруу",
    boardsManagement: "Канбан такталары",
    addUser: "Жаңы колдонуучу",
    addBoard: "Такта түзүү",
    fullName: "Аты-жөнү",
    email: "Email / Логин",
    phone: "Телефон",
    role: "Системадагы ролу",
    department: "Бөлүм",
    assignedBoard: "Бекемделген такта (бирөө гана)",
    status: "Абалы",
    active: "Иштеп жатат",
    blocked: "Бөгөттөлгөн",
    password: "Сыр сөз",
    resetPassword: "Сыр сөздү жаңыртуу",
    notifications: "Билдирүүлөр",
    noNotifications: "Жаңы билдирүүлөр жок",
    markAllRead: "Баарын окулду кылуу",
    noCardsYet: "Бул тилкеде тапшырмалар жок",
    noBoardsFound: "Жеткиликтүү такталар жок",
    changeBackground: "Фондун түсү",
    selectLanguageVariant: "Кытай тилинин түрү",
    attendance: "Убакытты эсептөө",
    checkIn: "Келди",
    checkOut: "Кетти",
    leaveBreak: "Чыгып кетти",
    resumeBreak: "Кайтты",
    inOffice: "Офисте",
    outsideOffice: "Офистен тышкары",
    onBreak: "Тыныгууда",
    notCheckedIn: "Сменада эмес",
    timesheet: "Табель",
    myAttendance: "Менин белгилерим",
    teamTimesheet: "Кызматкерлердин табели",
    officesAndSchedules: "Офистер жана графиктер",
    lateArrivals: "Кечикүүлөр",
    earlyDepartures: "Эрте кетүүлөр",
    workedHours: "Иштелген сааттар",
    vacation: "Эмгек өргүүсү",
    sickLeave: "Оору өргүүсү",
    businessTrip: "Иш сапар",
    dayOff: "Дем алыш күн",
    lunch: "Түшкү тамак",
    businessBreak: "Компаниянын жумушу боюнча",
    personalBreak: "Жеке иштер боюнча",
    otherBreak: "Башка себеп",
    editRecord: "Белгини оңдоо",
    mandatoryReason: "Оңдоонун милдеттүү себеби",
    locationConsent: "Геолокацияны көзөмөлдөөгө макулдук",
    consentGranted: "Макулдук берилген",
    grantConsent: "Макулдук берүү",
    revokeConsent: "Макулдукту артка кайтаруу",
    radiusMeters: "Радиус (метр)",
  }
};

export * from './translator';
import { toTraditionalChinese, toSimplifiedChinese, localizeDynamicText } from './translator';

export function getLocalizedText(
  obj: { title_ru?: string; title_zh?: string; title_ky?: string; desc_ru?: string; desc_zh?: string; desc_ky?: string; text_ru?: string; text_zh?: string; text_ky?: string; original_lang?: string },
  field: 'title' | 'desc' | 'text',
  lang: LanguageCode,
  showOriginal = false
): string {
  if (showOriginal && obj.original_lang) {
    const origKey = `${field}_${obj.original_lang}` as keyof typeof obj;
    if (obj[origKey]) return String(obj[origKey]);
  }

  if (lang === 'ky') {
    const kyVal = obj[`${field}_ky` as keyof typeof obj];
    if (kyVal) return String(kyVal);
    const ruVal = obj[`${field}_ru` as keyof typeof obj];
    return ruVal ? localizeDynamicText(String(ruVal), 'ky') : '';
  } else if (lang === 'zh-Hant') {
    const zhVal = obj[`${field}_zh` as keyof typeof obj];
    if (zhVal) return toTraditionalChinese(String(zhVal));
    const ruVal = obj[`${field}_ru` as keyof typeof obj];
    return ruVal ? localizeDynamicText(String(ruVal), 'zh-Hant') : '';
  } else if (lang === 'zh-Hans') {
    const zhVal = obj[`${field}_zh` as keyof typeof obj];
    if (zhVal) return toSimplifiedChinese(String(zhVal));
    const ruVal = obj[`${field}_ru` as keyof typeof obj];
    return ruVal ? localizeDynamicText(String(ruVal), 'zh-Hans') : '';
  }

  // ru language fallback
  const ruVal = obj[`${field}_ru` as keyof typeof obj];
  if (ruVal) return String(ruVal);
  return String(obj[`${field}_zh` as keyof typeof obj] || obj[`${field}_ky` as keyof typeof obj] || '');
}
