export const measureIds = ['qlikgpt_shared_revenue', 'qlikgpt_shared_orders',
  'qlikgpt_shared_margin', 'qlikgpt_shared_margin_pct'];
export const filters = [
  { key: 'year', id: 'qlikgpt_d_year', label: 'Anno' },
  { key: 'market', id: 'qlikgpt_d_market', label: 'Mercato' },
  { key: 'channel', id: 'qlikgpt_d_channel', label: 'Canale' },
];
export function cube(measures, dimension) {
  return { qDimensions: dimension ? [{ qLibraryId: dimension, qNullSuppression: true }] : [],
    qMeasures: measures.map(qLibraryId => ({ qLibraryId })), qStateName: '$',
    qSuppressMissing: true, qSuppressZero: false,
    qInitialDataFetch: [{ qTop: 0, qLeft: 0, qWidth: measures.length + (dimension ? 1 : 0), qHeight: dimension ? 100 : 1 }] };
}
export function sessionDefinitions() {
  return [
    { key: 'trend', props: { qInfo: { qType: 'qlikgpt-premium-trend' },
      qHyperCubeDef: cube([measureIds[0]], 'qlikgpt_d_yearmonth') } },
    { key: 'markets', props: { qInfo: { qType: 'qlikgpt-premium-markets' },
      qHyperCubeDef: cube([measureIds[0]], 'qlikgpt_d_market') } },
    ...filters.map(f => ({ key: f.key, props: {
      qInfo: { qType: 'qlikgpt-premium-filter' }, qListObjectDef: {
        qLibraryId: f.id, qStateName: '$',
        qInitialDataFetch: [{ qTop: 0, qLeft: 0, qWidth: 1, qHeight: 1000 }] } } })),
  ];
}
export const matrix = obj => obj?.qHyperCube?.qDataPages?.flatMap(p => p.qMatrix) || [];
export function rows(obj) {
  return matrix(obj).filter(r => !r[0].qIsNull && Number.isFinite(r[1]?.qNum))
    .map(r => ({ name: r[0].qText, sort: r[0].qNum, elem: r[0].qElemNumber,
      value: r[1].qNum, text: r[1].qText }));
}
