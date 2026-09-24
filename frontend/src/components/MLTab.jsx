import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { Cpu, Target, Crosshair, TrendingUp } from 'lucide-react';

const rocData = [
    { fpr: 0, tpr: 0 },
    { fpr: 0.05, tpr: 0.65 },
    { fpr: 0.1, tpr: 0.78 },
    { fpr: 0.15, tpr: 0.85 },
    { fpr: 0.2, tpr: 0.89 },
    { fpr: 0.3, tpr: 0.93 },
    { fpr: 0.5, tpr: 0.96 },
    { fpr: 0.8, tpr: 0.98 },
    { fpr: 1, tpr: 1 },
];

const featureImportance = [
    { name: 'Elevation', value: 0.32 },
    { name: 'Dist. Water', value: 0.25 },
    { name: 'Slope', value: 0.18 },
    { name: 'Landuse Code', value: 0.12 },
    { name: 'Dist. Road', value: 0.08 },
    { name: 'Dist. Bld.', value: 0.05 },
];

const MLTab = () => {
    return (
        <div className="content-pane">
            <div style={{ marginBottom: '2.5rem' }}>
                <h2>Machine Learning Insights</h2>
                <p className="p-text">
                    Our models evaluate thousands of spatial relationships to predict settlement probability.
                    The current flagship model is a highly tuned Random Forest Classifier trained over 1:10 synthetic samples.
                </p>
            </div>

            <div className="grid-3" style={{ marginBottom: '2.5rem' }}>
                <div className="stat-card">
                    <div className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Target size={32} /> 0.894
                    </div>
                    <div className="stat-label">Model AUC-ROC</div>
                </div>

                <div className="stat-card">
                    <div className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Crosshair size={32} /> 87%
                    </div>
                    <div className="stat-label">Precision (Class 1)</div>
                </div>

                <div className="stat-card">
                    <div className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <TrendingUp size={32} /> 200
                    </div>
                    <div className="stat-label">Random Forest Estimators</div>
                </div>
            </div>

            <div className="grid-2">
                <div className="card">
                    <h3 className="card-title">ROC Curve</h3>
                    <p className="p-text" style={{ fontSize: '0.9rem' }}>
                        Demonstrates excellent separation between known ancient sites and background sampling points.
                    </p>
                    <div style={{ height: '300px', margin: '2rem 0 1rem 0' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={rocData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                <XAxis dataKey="fpr" stroke="#cbd5e1" label={{ value: 'False Positive Rate', position: 'insideBottom', offset: -10, fill: '#cbd5e1' }} />
                                <YAxis stroke="#cbd5e1" label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft', fill: '#cbd5e1' }} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: '#d97706', borderRadius: '8px' }}
                                    itemStyle={{ color: '#f59e0b' }}
                                />
                                <Area type="monotone" dataKey="tpr" stroke="#d97706" fill="url(#colorUv)" strokeWidth={3} />
                                <defs>
                                    <linearGradient id="colorUv" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#d97706" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="#d97706" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="card">
                    <h3 className="card-title">Feature Importance Gini</h3>
                    <p className="p-text" style={{ fontSize: '0.9rem' }}>
                        Elevation and proximity to historical waterways form the strongest predictive indicators.
                    </p>
                    <div style={{ height: '300px', margin: '2rem 0 1rem 0' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={featureImportance} margin={{ top: 10, right: 30, left: 0, bottom: 25 }} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                <XAxis type="number" stroke="#cbd5e1" />
                                <YAxis dataKey="name" type="category" width={100} stroke="#cbd5e1" />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: '#d97706', borderRadius: '8px' }}
                                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                />
                                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                                    {featureImportance.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={index === 0 ? '#b45309' : (index === 1 ? '#d97706' : '#f59e0b')} opacity={1 - (index * 0.15)} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MLTab;
