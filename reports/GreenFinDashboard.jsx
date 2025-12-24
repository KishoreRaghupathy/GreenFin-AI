import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { initializeApp } from 'firebase/app';
import { getAuth, signInWithCustomToken, signInAnonymously, onAuthStateChanged } from 'firebase/auth';
import { getFirestore, collection, query, onSnapshot, where, doc, setDoc } from 'firebase/firestore';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Loader2, Zap, AlertTriangle, CheckCircle, TrendingUp, TrendingDown, Users, DollarSign, Send } from 'lucide-react';

// --- Global Variables and Configuration ---
const appId = typeof __app_id !== 'undefined' ? __app_id : 'greenfin-default-app';
const firebaseConfig = JSON.parse(typeof __firebase_config !== 'undefined' ? __firebase_config : '{}');
const initialAuthToken = typeof __initial_auth_token !== 'undefined' ? __initial_auth_token : null;

// Mock data (matches the summary provided in the chat history)
const MOCK_DATA = [
    { tier: 'A: Leader (Low Risk)', exposure: 9933.22, percentage: 3.57, color: '#10B981', count: 34 }, // Emerald-500
    { tier: 'B: Aligned (Moderate Risk)', exposure: 86354.51, percentage: 31.05, color: '#3B82F6', count: 313 }, // Blue-500
    { tier: 'C: Watchlist (High Risk)', exposure: 129817.65, percentage: 46.67, color: '#F59E0B', count: 459 }, // Amber-500
    { tier: 'D: Divestment (Very High Risk)', exposure: 52052.43, percentage: 18.71, color: '#EF4444', count: 194 }, // Red-500
];
const TOTAL_EXPOSURE = 278157.81; // Total Portfolio Exposure (Mn)
const TIER_D_TARGET_EXPOSURE = 52052.43; // The initial value we aim to divest
const COLORS = MOCK_DATA.reduce((acc, d) => ({ ...acc, [d.tier]: d.color }), {});

// --- Firebase Initialization and Auth Logic ---
let db = null;
let auth = null;

const initializeFirebase = () => {
    if (!db) {
        try {
            const app = initializeApp(firebaseConfig);
            db = getFirestore(app);
            auth = getAuth(app);
            return true;
        } catch (error) {
            console.error("Firebase initialization failed:", error);
            return false;
        }
    }
    return true;
};


// --- Custom Components ---

const DataLoading = ({ message }) => (
    <div className="flex flex-col items-center justify-center p-8 bg-white/10 rounded-xl shadow-lg animate-pulse">
        <Loader2 className="w-10 h-10 text-indigo-400 animate-spin" />
        <p className="mt-4 text-lg font-semibold text-gray-300">{message}</p>
    </div>
);

const MetricCard = ({ title, value, unit, icon: Icon, colorClass, description }) => (
    <div className={`p-5 bg-gray-800 rounded-xl border-t-4 ${colorClass} shadow-2xl transition duration-300 hover:scale-[1.02]`}>
        <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium uppercase text-gray-400">{title}</h3>
            <Icon className={`w-6 h-6 ${colorClass.replace('border-', 'text-')}`} />
        </div>
        <p className="mt-1 text-3xl font-bold text-white">
            {value}
            <span className="ml-2 text-base font-normal text-gray-400">{unit}</span>
        </p>
        <p className="mt-2 text-xs text-gray-500">{description}</p>
    </div>
);

const DivestmentSimulator = ({ dbData, calculatedMetrics, userId }) => {
    const [divestmentAmount, setDivestmentAmount] = useState('');
    const [error, setError] = useState('');
    const [isUpdating, setIsUpdating] = useState(false);

    const docRef = useMemo(() => {
        const collectionPath = `artifacts/${appId}/public/data/portfolio_risk`;
        return db ? doc(db, collectionPath, 'portfolio_summary') : null;
    }, [db, appId]);

    const handleSimulateDivestment = async () => {
        const amount = parseFloat(divestmentAmount);
        setError('');

        if (isNaN(amount) || amount <= 0) {
            setError('Please enter a valid positive number for divestment.');
            return;
        }

        const currentTierD = dbData.riskData.find(d => d.tier.startsWith('D'));
        const currentTierDExposure = currentTierD ? currentTierD.exposure : 0;

        if (amount > currentTierDExposure) {
            setError(`Divestment amount ($${amount.toFixed(2)} Mn) exceeds remaining Tier D exposure ($${currentTierDExposure.toFixed(2)} Mn).`);
            return;
        }
        
        setIsUpdating(true);

        try {
            const newTierDExposure = currentTierDExposure - amount;
            
            // Calculate new percentage for Tier D
            const newTierDPercentage = (newTierDExposure / TOTAL_EXPOSURE) * 100;

            // Update the riskData array
            const updatedRiskData = dbData.riskData.map(d => {
                if (d.tier.startsWith('D')) {
                    return {
                        ...d,
                        exposure: newTierDExposure,
                        percentage: newTierDPercentage,
                    };
                } else if (d.tier.startsWith('C') && newTierDExposure <= 0) {
                    // Bonus: If Tier D is fully divested, move Watchlist (C) to a higher risk focus visually
                    // This is simple logic; real logic would be complex.
                    return {
                        ...d,
                        // Optionally update C tier visual/label
                    };
                }
                return d;
            });
            
            // Recalculate all percentages based on total exposure remaining the same (as divestment assumes asset transfer/sale)
            const recalculateTotal = updatedRiskData.reduce((sum, d) => sum + d.exposure, 0);
            const finalRiskData = updatedRiskData.map(d => ({
                ...d,
                percentage: (d.exposure / recalculateTotal) * 100
            }));
            

            await setDoc(docRef, {
                ...dbData, // Keep totalExposure, initialTierDTarget, etc.
                riskData: finalRiskData,
                lastUpdated: new Date().toISOString(),
                lastAction: {
                    type: 'Divestment',
                    amount: amount,
                    timestamp: new Date().toISOString(),
                    user: userId
                }
            });

            setDivestmentAmount('');
            console.log(`Divestment of $${amount.toFixed(2)} Mn simulated successfully.`);

        } catch (e) {
            console.error("Error simulating divestment:", e);
            setError("Failed to update portfolio data in Firestore.");
        } finally {
            setIsUpdating(false);
        }
    };

    const remainingExposure = calculatedMetrics.currentTierDExposure;

    return (
        <div className="p-6 bg-gray-800 rounded-xl shadow-2xl border-t-4 border-gray-500">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                <DollarSign className="w-5 h-5 mr-2 text-indigo-400"/>
                Simulate Divestment
            </h2>
            <p className="text-sm text-gray-400 mb-4">
                Enter the amount (in millions USD) of Tier D exposure that has been divested (sold or matured).
            </p>
            <div className="flex flex-col space-y-3">
                <label htmlFor="divestmentInput" className="text-sm font-medium text-gray-300">
                    Amount Divested (Mn USD)
                </label>
                <input
                    id="divestmentInput"
                    type="number"
                    value={divestmentAmount}
                    onChange={(e) => {
                        setDivestmentAmount(e.target.value);
                        setError(''); // Clear error on input change
                    }}
                    placeholder={`Max remaining: ${remainingExposure.toFixed(2)}`}
                    className="p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:ring-green-500 focus:border-green-500 transition"
                    disabled={isUpdating || remainingExposure <= 0}
                />
                <button
                    onClick={handleSimulateDivestment}
                    className="flex items-center justify-center p-3 font-bold text-white bg-green-600 rounded-lg shadow-md hover:bg-green-500 transition disabled:bg-gray-600 disabled:cursor-not-allowed"
                    disabled={isUpdating || !divestmentAmount || remainingExposure <= 0}
                >
                    {isUpdating ? (
                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    ) : (
                        <Send className="w-5 h-5 mr-2" />
                    )}
                    {remainingExposure <= 0 ? 'Target Achieved!' : 'Commit Divestment'}
                </button>
            </div>
            {error && (
                <p className="mt-3 text-sm text-red-400 p-2 bg-red-900/30 rounded-lg">
                    {error}
                </p>
            )}
            {dbData.lastAction && (
                <div className="mt-4 text-xs text-gray-500 border-t border-gray-700 pt-3">
                    Last Action: ${dbData.lastAction.amount.toFixed(2)} Mn divested by {dbData.lastAction.user} on {new Date(dbData.lastAction.timestamp).toLocaleDateString()}
                </div>
            )}
        </div>
    );
};

// --- Main App Component ---

const App = () => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [userId, setUserId] = useState(null);
    const [dbData, setDbData] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    // 1. Firebase Initialization and Authentication
    useEffect(() => {
        if (!initializeFirebase()) {
            setIsLoading(false);
            return;
        }

        const authenticate = async () => {
            try {
                if (initialAuthToken) {
                    await signInWithCustomToken(auth, initialAuthToken);
                } else {
                    await signInAnonymously(auth);
                }
            } catch (error) {
                console.error("Authentication failed:", error);
            }
        };

        const unsubscribeAuth = onAuthStateChanged(auth, (user) => {
            if (user) {
                setUserId(user.uid);
                setIsAuthenticated(true);
                console.log(`User authenticated: ${user.uid}`);
            } else {
                setUserId(null);
                setIsAuthenticated(false);
                console.log("User signed out/anonymous.");
            }
            setIsLoading(false);
        });

        authenticate();
        return () => unsubscribeAuth();
    }, []);

    // 2. Data Fetching (Firestore Listener)
    useEffect(() => {
        if (!isAuthenticated || !db || !userId) return;

        // Public collection path: /artifacts/{appId}/public/data/portfolio_risk
        const collectionPath = `artifacts/${appId}/public/data/portfolio_risk`;
        
        // Use a persistent 'portfolio_summary' document to store the data
        const docRef = doc(db, collectionPath, 'portfolio_summary');
        
        // --- Mock Data Insertion (One-time, if document doesn't exist) ---
        const initializeData = async () => {
             // In a real app, this would be imported from the esg_loan_analysis.py report data
             try {
                // Combine MOCK_DATA with counts
                const initialRiskData = MOCK_DATA.map(d => ({
                    ...d,
                    count: d.count || (d.tier.startsWith('A') ? 34 : d.tier.startsWith('B') ? 313 : d.tier.startsWith('C') ? 459 : 194) // Ensure counts are present
                }));

                await setDoc(docRef, {
                    totalExposure: TOTAL_EXPOSURE,
                    initialTierDTarget: TIER_D_TARGET_EXPOSURE,
                    lastUpdated: new Date().toISOString(),
                    riskData: initialRiskData,
                    lastAction: null, // Initialize last action
                }, { merge: true });
                console.log("Mock data ensured in Firestore.");
            } catch (e) {
                console.error("Error setting initial document: ", e);
            }
        };

        initializeData();
        
        // --- Real-Time Listener ---
        const unsubscribeSnapshot = onSnapshot(docRef, (docSnapshot) => {
            if (docSnapshot.exists()) {
                const data = docSnapshot.data();
                setDbData(data);
                console.log("Real-time data updated from Firestore.");
            } else {
                console.warn("Portfolio summary document does not exist.");
            }
        }, (error) => {
            console.error("Error listening to Firestore:", error);
        });

        return () => unsubscribeSnapshot();
    }, [isAuthenticated, userId]); // Re-run when auth state changes

    // --- Derived State and Calculations ---

    const calculatedMetrics = useMemo(() => {
        if (!dbData) return {};
        
        const currentTierD = dbData.riskData.find(d => d.tier.startsWith('D'));
        const currentTierDExposure = currentTierD ? currentTierD.exposure : 0;
        
        const totalTarget = dbData.initialTierDTarget;
        const progressMade = Math.max(0, totalTarget - currentTierDExposure); // Ensure progress isn't negative
        
        // Calculate progress percentage, handling division by zero if target is 0 
        const progressPercentage = totalTarget > 0 ? (progressMade / totalTarget) * 100 : 0;
        
        const tierC = dbData.riskData.find(d => d.tier.startsWith('C'));
        const highRiskExposure = currentTierDExposure + (tierC ? tierC.exposure : 0);
        
        // Total count calculation for the Metric Card description
        const totalLoanCount = dbData.riskData.reduce((a, b) => a + (b.count || 0), 0);

        return {
            currentTierDExposure,
            progressMade,
            progressPercentage: Math.min(100, progressPercentage), // Cap percentage at 100
            highRiskExposure,
            totalLoanCount
        };

    }, [dbData]);

    const chartData = dbData ? dbData.riskData.map(d => ({
        name: d.tier.split(':')[0],
        value: parseFloat(d.exposure.toFixed(2)),
        exposure: d.exposure,
        percentage: d.percentage,
        tier: d.tier // Keep full tier name for Tooltip
    })) : [];

    if (isLoading) {
        return <div className="h-screen flex items-center justify-center bg-gray-900"><DataLoading message="Authenticating and loading portfolio data..." /></div>;
    }
    if (!isAuthenticated) {
        return <div className="p-8 text-center text-red-500 bg-gray-900 h-screen">Authentication failed. Please refresh the canvas.</div>;
    }
    if (!dbData) {
        return <div className="p-8 text-center text-yellow-500 bg-gray-900 h-screen"><DataLoading message="Waiting for portfolio data from Firestore..." /></div>;
    }

    return (
        <div className="min-h-screen p-6 bg-gray-900 text-white font-sans">
            <header className="flex justify-between items-center pb-6 border-b border-gray-700 mb-6">
                <h1 className="text-3xl font-extrabold text-green-400">GreenFin Decoupling Strategy Dashboard</h1>
                <div className="flex items-center text-sm text-gray-400">
                    <Users className="w-4 h-4 mr-1 text-gray-500" />
                    User ID: <code className="ml-1 text-xs text-yellow-400">{userId}</code>
                </div>
            </header>

            {/* Metric Cards Row */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <MetricCard 
                    title="Total Portfolio Exposure" 
                    value={(dbData.totalExposure / 1000).toFixed(1)} 
                    unit="Bn USD" 
                    icon={TrendingUp}
                    colorClass="border-indigo-400"
                    description={`Calculated from ${calculatedMetrics.totalLoanCount} total loans.`}
                />
                <MetricCard 
                    title="Tier D Exposure Remaining" 
                    value={calculatedMetrics.currentTierDExposure.toFixed(2)} 
                    unit="Mn USD" 
                    icon={Zap}
                    colorClass="border-red-400"
                    description={`Target Divestment: ${dbData.initialTierDTarget.toFixed(2)} Mn.`}
                />
                <MetricCard 
                    title="Divestment Progress" 
                    value={calculatedMetrics.progressPercentage.toFixed(1)} 
                    unit="%" 
                    icon={CheckCircle}
                    colorClass="border-green-400"
                    description={`${calculatedMetrics.progressMade.toFixed(2)} Mn divested/reduced so far.`}
                />
                 <MetricCard 
                    title="Total High Risk (C+D)" 
                    value={calculatedMetrics.highRiskExposure.toFixed(2)} 
                    unit="Mn USD" 
                    icon={AlertTriangle}
                    colorClass="border-yellow-400"
                    description={`The exposure requiring immediate management attention.`}
                />
            </div>

            {/* Chart, Simulator, and Loan List */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Divestment Simulator Card */}
                <DivestmentSimulator 
                    dbData={dbData} 
                    calculatedMetrics={calculatedMetrics} 
                    userId={userId} 
                />

                {/* Portfolio Distribution Chart */}
                <div className="lg:col-span-2 p-6 bg-gray-800 rounded-xl shadow-2xl">
                    <h2 className="text-xl font-semibold mb-4 text-white">Portfolio Exposure Distribution (Mn USD)</h2>
                    <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                            <Pie
                                data={chartData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={120}
                                fill="#8884d8"
                                paddingAngle={2}
                                dataKey="value"
                            >
                                {chartData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[dbData.riskData[index].tier]} stroke={COLORS[dbData.riskData[index].tier]} />
                                ))}
                            </Pie>
                            <Tooltip 
                                contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                                formatter={(value, name, props) => [`$${value.toLocaleString()} Mn (${props.payload.percentage.toFixed(2)}%)`, props.payload.tier]}
                                labelFormatter={(label) => 'Exposure'}
                            />
                            <Legend layout="horizontal" verticalAlign="bottom" align="center" wrapperStyle={{ paddingTop: '10px' }} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>
            
            {/* Loan Review Table - Moved outside the grid for better flow */}
            <div className="mt-6 p-6 bg-gray-800 rounded-xl shadow-2xl overflow-x-auto">
                <h2 className="text-xl font-semibold mb-4 text-white">Critical Loan Review: Top & Bottom Performers</h2>
                <table className="min-w-full divide-y divide-gray-700">
                    <thead className="bg-gray-700">
                        <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Borrower</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Sector</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Exposure (Mn)</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Score</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Risk Tier</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                        {/* Mock Data for Top 5 (Leader) */}
                        <tr className="bg-gray-800">
                            <td colSpan="5" className="px-4 py-2 text-sm font-bold text-green-400 bg-gray-700/50">Leaders (A-Tier) - Maintain & Scale</td>
                        </tr>
                        {MOCK_DATA.find(d => d.tier.startsWith('A')) && [
                            // These are mock, hardcoded examples from the previous python output
                            { name: 'Borrower 758', sector: 'Tech Services', exposure: 269.53, score: 94.47, tier: 'A' },
                            { name: 'Borrower 299', sector: 'Tech Services', exposure: 336.39, score: 93.97, tier: 'A' },
                            { name: 'Borrower 804', sector: 'Tech Services', exposure: 183.44, score: 93.47, tier: 'A' },
                            { name: 'Borrower 21', sector: 'Tech Services', exposure: 363.84, score: 92.97, tier: 'A' },
                            { name: 'Borrower 942', sector: 'Tech Services', exposure: 200.41, score: 88.97, tier: 'A' },
                        ].map((loan, index) => (
                            <tr key={`top-${index}`} className="hover:bg-gray-700 transition duration-150">
                                <td className="px-4 py-2 text-sm font-medium">{loan.name}</td>
                                <td className="px-4 py-2 text-sm text-gray-400">{loan.sector}</td>
                                <td className="px-4 py-2 text-sm text-green-300">${loan.exposure.toFixed(2)}</td>
                                <td className="px-4 py-2 text-sm text-green-300 font-semibold">{loan.score.toFixed(2)}</td>
                                <td className="px-4 py-2 text-sm text-green-400">A</td>
                            </tr>
                        ))}
                        
                        {/* Mock Data for Bottom 5 (Divestment) */}
                        <tr className="bg-gray-800">
                            <td colSpan="5" className="px-4 py-2 text-sm font-bold text-red-400 bg-gray-700/50">Divestment Candidates (D-Tier) - Exit Strategy</td>
                        </tr>
                        {MOCK_DATA.find(d => d.tier.startsWith('D')) && [
                            // These are mock, hardcoded examples from the previous python output
                            { name: 'Borrower 834', sector: 'Oil & Gas', exposure: 386.63, score: 19.86, tier: 'D' },
                            { name: 'Borrower 80', sector: 'Oil & Gas', exposure: 477.48, score: 18.36, tier: 'D' },
                            { name: 'Borrower 477', sector: 'Oil & Gas', exposure: 413.53, score: 16.86, tier: 'D' },
                            { name: 'Borrower 795', sector: 'Oil & Gas', exposure: 68.75, score: 13.86, tier: 'D' },
                            { name: 'Borrower 889', sector: 'Oil & Gas', exposure: 376.91, score: 13.36, tier: 'D' },
                        ].map((loan, index) => (
                            <tr key={`bottom-${index}`} className="hover:bg-gray-700 transition duration-150">
                                <td className="px-4 py-2 text-sm font-medium">{loan.name}</td>
                                <td className="px-4 py-2 text-sm text-gray-400">{loan.sector}</td>
                                <td className="px-4 py-2 text-sm text-red-300">${loan.exposure.toFixed(2)}</td>
                                <td className="px-4 py-2 text-sm text-red-300 font-semibold">{loan.score.toFixed(2)}</td>
                                <td className="px-4 py-2 text-sm text-red-400">D</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>


            <footer className="mt-8 pt-4 border-t border-gray-700 text-center text-sm text-gray-500">
                Data reflects initial portfolio load on {new Date().toLocaleDateString()}. Exposure tracked in real-time via Firestore.
            </footer>
        </div>
    );
};

export default App;