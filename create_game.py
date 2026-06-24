import os

PROJECT_NAME = "digital-empire-vk"

files = {
    ".gitignore": """node_modules/
dist/
.env
*.local
""",
    
    "package.json": """{
  "name": "digital-empire-vk",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@vkontakte/vk-bridge": "^2.7.2",
    "@vkontakte/vkui": "^5.0.2",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "supabase": "^2.39.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.2.2",
    "vite": "^5.0.8"
  }
}""",

    "vite.config.ts": """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173
  }
})""",

    "tsconfig.json": """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}""",

    "tsconfig.node.json": """{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}""",

    "index.html": """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>Digital Empire</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>""",

    "supabase/schema.sql": """CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vk_id BIGINT UNIQUE NOT NULL,
    first_name TEXT,
    last_name TEXT,
    photo_200 TEXT,
    referrer_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE game_state (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    money BIGINT DEFAULT 0,
    total_earned BIGINT DEFAULT 0,
    lifetime_earned BIGINT DEFAULT 0,
    prestige_points BIGINT DEFAULT 0,
    prestige_multiplier NUMERIC(10, 2) DEFAULT 1.00,
    last_active TIMESTAMPTZ DEFAULT NOW(),
    businesses JSONB DEFAULT '{\\n        "startup": { "owned": 0, "level": 0 },\\n        "app": { "owned": 0, "level": 0 },\\n        "saas": { "owned": 0, "level": 0 },\\n        "cloud": { "owned": 0, "level": 0 },\\n        "ai": { "owned": 0, "level": 0 }\\n    }'::jsonb
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    type TEXT NOT NULL,
    amount BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_vk_id ON users(vk_id);
CREATE INDEX idx_game_state_lifetime ON game_state(lifetime_earned DESC);

CREATE MATERIALIZED VIEW leaderboard AS
SELECT u.vk_id, u.first_name, u.photo_200, g.lifetime_earned, g.prestige_points
FROM users u JOIN game_state g ON u.id = g.user_id
ORDER BY g.lifetime_earned DESC;

CREATE OR REPLACE FUNCTION claim_offline_income(p_user_id UUID)
RETURNS BIGINT AS $$ DECLARE
    v_state game_state%ROWTYPE;
    v_seconds BIGINT;
    v_offline_income BIGINT := 0;
    v_income_per_sec BIGINT := 0;
    v_biz_key TEXT;
    v_biz_data JSONB;
BEGIN
    SELECT * INTO v_state FROM game_state WHERE user_id = p_user_id;
    IF v_state IS NULL THEN RETURN 0; END IF;
    
    v_seconds := GREATEST(EXTRACT(EPOCH FROM (NOW() - v_state.last_active))::BIGINT, 0);
    v_seconds := LEAST(v_seconds, 43200);
    
    FOR v_biz_key IN SELECT jsonb_object_keys(v_state.businesses) LOOP
        v_biz_data := v_state.businesses -> v_biz_key;
        IF (v_biz_data ->> 'owned')::INT > 0 THEN
            v_income_per_sec := v_income_per_sec + ((v_biz_data ->> 'owned')::INT * (v_biz_data ->> 'level')::INT * 10);
        END IF;
    END LOOP;
    
    v_offline_income := v_income_per_sec * v_seconds * v_state.prestige_multiplier::BIGINT;
    
    UPDATE game_state 
    SET money = money + v_offline_income, total_earned = total_earned + v_offline_income,
        lifetime_earned = lifetime_earned + v_offline_income, last_active = NOW()
    WHERE user_id = p_user_id;
    
    RETURN v_offline_income;
END;
 $$ LANGUAGE plpgsql;""",

    "src/main.tsx": """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);""",

    "src/index.css": """* { margin: 0; padding: 0; box-sizing: border-box; }
body { background-color: var(--vkui--color_background); font-family: -apple-system, BlinkMacSystemFont, Roboto, Helvetica Neue, sans-serif; }
vkui-root, vkui-view, vkui-panel { -webkit-tap-highlight-color: transparent; user-select: none; }""",

    "src/types/index.ts": """export interface BusinessConfig {
    id: string; name: string; icon: string; baseCost: number; baseIncome: number; costMultiplier: number; timeToEarn: number;
}
export interface UserBusinessState { owned: number; level: number; progress: number; }
export interface GameState {
    money: number; totalEarned: number; lifetimeEarned: number; prestigePoints: number; prestigeMultiplier: number;
    businesses: Record<string, UserBusinessState>;
}
export interface VKUser { id: number; first_name: string; last_name: string; photo_200?: string; }""",

    "src/engine/constants.ts": """import { BusinessConfig } from '../types';
export const BUSINESSES: BusinessConfig[] = [
    { id: 'startup', name: 'Стартап', icon: '💡', baseCost: 10, baseIncome: 1, costMultiplier: 1.15, timeToEarn: 1000 },
    { id: 'app', name: 'Приложение', icon: '📱', baseCost: 120, baseIncome: 15, costMultiplier: 1.15, timeToEarn: 3000 },
    { id: 'saas', name: 'SaaS', icon: '☁️', baseCost: 1500, baseIncome: 200, costMultiplier: 1.15, timeToEarn: 6000 },
    { id: 'cloud', name: 'Облако', icon: '🖥️', baseCost: 25000, baseIncome: 3500, costMultiplier: 1.15, timeToEarn: 12000 },
    { id: 'ai', name: 'ИИ Корп.', icon: '🤖', baseCost: 500000, baseIncome: 80000, costMultiplier: 1.15, timeToEarn: 24000 },
];
export const PRESTIGE_BASE_MULTIPLIER = 1e6;""",

    "src/engine/economy.ts": """import { BusinessConfig, GameState, UserBusinessState } from '../types';
import { BUSINESSES, PRESTIGE_BASE_MULTIPLIER } from './constants';

export const calculateCost = (config: BusinessConfig, owned: number): number => Math.floor(config.baseCost * Math.pow(config.costMultiplier, owned));
export const calculateIncomePerSecond = (config: BusinessConfig, state: UserBusinessState, prestigeMult: number): number => {
    if (state.owned === 0) return 0;
    return (state.owned * config.baseIncome * (1 + (state.level * 0.5))) * prestigeMult;
};
export const calculatePrestigeGain = (lifetimeEarned: number): number => Math.floor(Math.sqrt(lifetimeEarned / PRESTIGE_BASE_MULTIPLIER));
export const calculatePrestigeMultiplier = (totalPoints: number): number => 1 + (totalPoints * 0.1);
export const getInitialGameState = (): GameState => ({
    money: 0, totalEarned: 0, lifetimeEarned: 0, prestigePoints: 0, prestigeMultiplier: 1,
    businesses: BUSINESSES.reduce((acc, b) => { acc[b.id] = { owned: 0, level: 0, progress: 0 }; return acc; }, {} as Record<string, UserBusinessState>)
});""",

    "src/vk/bridge.ts": """import * as bridge from '@vkontakte/vk-bridge';
export const initVK = async () => { await bridge.send('VKWebAppInit'); };
export const getVKUser = async () => { return await bridge.send('VKWebAppGetUserInfo'); };
export const showRewardedAd = async () => { try { return (await bridge.send('VKWebAppShowNativeAds', { ad_format: 'reward' })).result; } catch (e) { return false; } };
export const inviteFriends = () => { bridge.send('VKWebAppShowInviteBox', {}); };
export const openPaywall = () => { bridge.send('VKWebAppOpenPaywall', {}); };""",

    "src/api/supabase.ts": """import { createClient, SupabaseClient } from '@supabase/supabase-js';
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;
if (!SUPABASE_URL || !SUPABASE_ANON_KEY) throw new Error("Missing Supabase env vars");
export const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

export const fetchGameState = async (vkId: number) => {
    let { data: user } = await supabase.from('users').select('id').eq('vk_id', vkId).single();
    if (!user) { const { data: newUser } = await supabase.from('users').insert({ vk_id: vkId }).select('id').single(); user = newUser; await supabase.from('game_state').insert({ user_id: user.id }); }
    await supabase.rpc('claim_offline_income', { p_user_id: user.id });
    const { data: state } = await supabase.from('game_state').select('*').eq('user_id', user.id).single();
    return state;
};

export const saveGameState = async (vkId: number, state: any) => {
    let { data: user } = await supabase.from('users').select('id').eq('vk_id', vkId).single();
    if (!user) return;
    await supabase.from('game_state').update({ money: state.money, total_earned: state.totalEarned, lifetime_earned: state.lifetimeEarned, prestige_points: state.prestigePoints, prestige_multiplier: state.prestigeMultiplier, businesses: state.businesses, last_active: new Date().toISOString() }).eq('user_id', user.id);
};

export const fetchLeaderboard = async () => { const { data } = await supabase.from('leaderboard').select('*').limit(20); return data; };""",

    "src/components/BusinessCard.tsx": """import React from 'react';
import { Card, Div, Text, Button, Progress, Counter } from '@vkontakte/vkui';
import { BusinessConfig, UserBusinessState } from '../types';
import { calculateCost, calculateIncomePerSecond } from '../engine/economy';

interface Props { config: BusinessConfig; state: UserBusinessState; money: number; prestigeMult: number; onBuy: (id: string) => void; onUpgrade: (id: string) => void; }

export const BusinessCard: React.FC<Props> = ({ config, state, money, prestigeMult, onBuy, onUpgrade }) => {
    const cost = calculateCost(config, state.owned);
    const canBuy = money >= cost;
    const incomePerSec = calculateIncomePerSecond(config, state, prestigeMult);
    const upgradeCost = state.owned > 0 ? Math.floor(cost * 5) : 0;
    return (
        <Card mode="outline" style={{ marginBottom: 12, padding: 12 }}>
            <Div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span style={{ fontSize: 32, marginRight: 12 }}>{config.icon}</span>
                    <div>
                        <Text weight="2">{config.name}</Text>
                        <Text style={{ color: 'var(--vkui--color_text_subsecondary)' }} weight="3">{incomePerSec > 0 ? `$${incomePerSec.toLocaleString()}/сек` : 'Не куплено'}</Text>
                    </div>
                </div>
                <div style={{ textAlign: 'right' }}><Counter mode={canBuy ? 'primary' : 'secondary'}>$${cost.toLocaleString()}</Counter></div>
            </Div>
            {state.owned > 0 && (
                <Div style={{ paddingTop: 0, paddingBottom: 0 }}>
                    <Progress value={state.progress} style={{ marginBottom: 8 }} />
                    <Button mode="tertiary" size="s" disabled={money < upgradeCost} onClick={() => onUpgrade(config.id)} style={{ float: 'right' }}>Улучшить (${Math.floor(upgradeCost).toLocaleString()})</Button>
                    <Text weight="3" style={{ color: 'var(--vkui--color_text_subsecondary)' }}>Ур: {state.level} | Кол-во: {state.owned}</Text>
                </Div>
            )}
            <Div style={{ paddingTop: state.owned > 0 ? 8 : 0 }}>
                <Button stretched mode="commerce" size="l" disabled={!canBuy} onClick={() => onBuy(config.id)}>{state.owned === 0 ? 'Запустить' : 'Купить еще'}</Button>
            </Div>
        </Card>
    );
};""",

    "src/components/PrestigePanel.tsx": """import React from 'react';
import { Div, Button, Title, Text, ModalPage, ModalPageHeader } from '@vkontakte/vkui';
import { calculatePrestigeGain } from '../engine/economy';

interface Props { lifetimeEarned: number; currentPoints: number; onPrestige: () => void; onClose: () => void; }

export const PrestigePanel: React.FC<Props> = ({ lifetimeEarned, currentPoints, onPrestige, onClose }) => {
    const gain = calculatePrestigeGain(lifetimeEarned);
    return (
        <ModalPage id="prestige" header={<ModalPageHeader>Сброс и Престиж</ModalPageHeader>} onClose={onClose}>
            <Div style={{ textAlign: 'center' }}>
                <Title level="3">Создать новую империю?</Title>
                <Text style={{ margin: '16px 0' }}>Вы потеряете все бизнесы, но получите множитель дохода навсегда.</Text>
                <Title level="2" style={{ color: 'var(--vkui--color_text_accent)' }}>+{gain} Очков</Title>
                <Text style={{ marginBottom: 16 }}>Текущих: {currentPoints}</Text>
                <Button size="l" stretched mode="destructive" disabled={gain <= 0} onClick={onPrestige}>ПРЕСТИЖ</Button>
            </Div>
        </ModalPage>
    );
};""",

    "src/components/Leaderboard.tsx": """import React from 'react';
import { Text, Avatar, SimpleCell, Group } from '@vkontakte/vkui';
export const Leaderboard: React.FC<{ data: any[] }> = ({ data }) => (
    <Group header={<Text weight="2">Топ Империй</Text>}>
        {data && data.map((row, i) => (
            <SimpleCell key={row.vk_id} before={<Avatar size={40} src={row.photo_200} />} after={<Text weight="2">${row.lifetime_earned > 1e9 ? `${(row.lifetime_earned/1e9).toFixed(1)}B` : `${(row.lifetime_earned/1e6).toFixed(1)}M`}</Text>} description={`Престиж: ${row.prestige_points}`}>
                {i + 1}. {row.first_name}
            </SimpleCell>
        ))}
    </Group>
);""",

    "src/components/Monetization.tsx": """import React from 'react';
import { Div, Button, HorizontalScroll, Card } from '@vkontakte/vkui';
import { showRewardedAd, inviteFriends, openPaywall } from '../vk/bridge';
export const Monetization: React.FC<{ onAdWatch: () => void }> = ({ onAdWatch }) => {
    const handleAd = async () => { if (await showRewardedAd()) onAdWatch(); };
    return (
        <Div>
            <HorizontalScroll>
                <div style={{ display: 'flex', gap: 8 }}>
                    <Card mode="outline" style={{ minWidth: 150, padding: 12, textAlign: 'center' }}><div style={{ fontSize: 24 }}>📺</div><Button mode="outline" size="s" onClick={handleAd} style={{ marginTop: 8 }}>х2 За 5 мин</Button></Card>
                    <Card mode="outline" style={{ minWidth: 150, padding: 12, textAlign: 'center' }}><div style={{ fontSize: 24 }}>👑</div><Button mode="outline" size="s" onClick={openPaywall} style={{ marginTop: 8 }}>VIP</Button></Card>
                    <Card mode="outline" style={{ minWidth: 150, padding: 12, textAlign: 'center' }}><div style={{ fontSize: 24 }}>👥</div><Button mode="outline" size="s" onClick={inviteFriends} style={{ marginTop: 8 }}>+5% За друга</Button></Card>
                </div>
            </HorizontalScroll>
        </Div>
    );
};""",

    "src/App.tsx": """import React, { useEffect, useState, useCallback, useRef } from 'react';
import { View, Panel, PanelHeader, Title, ScreenSpinner, ModalRoot } from '@vkontakte/vkui';
import '@vkontakte/vkui/dist/vkui.css';
import { initVK, getVKUser } from './vk/bridge';
import { fetchGameState, saveGameState, fetchLeaderboard } from './api/supabase';
import { BUSINESSES } from './engine/constants';
import { calculateCost, calculateIncomePerSecond, calculatePrestigeGain, calculatePrestigeMultiplier, getInitialGameState } from './engine/economy';
import { GameState, VKUser } from './types';
import { BusinessCard } from './components/BusinessCard';
import { PrestigePanel } from './components/PrestigePanel';
import { Leaderboard } from './components/Leaderboard';
import { Monetization } from './components/Monetization';

const App: React.FC = () => {
    const [vkUser, setVkUser] = useState<VKUser | null>(null);
    const [game, setGame] = useState<GameState>(getInitialGameState());
    const [loading, setLoading] = useState(true);
    const [leaderboard, setLeaderboard] = useState<any[]>([]);
    const [activeModal, setActiveModal] = useState<string | null>(null);
    const gameRef = useRef(game);
    gameRef.current = game;

    useEffect(() => {
        const init = async () => {
            await initVK();
            const user = await getVKUser();
            setVkUser(user);
            if (user) {
                const state = await fetchGameState(user.id);
                if (state) setGame({ money: state.money, totalEarned: state.total_earned, lifetimeEarned: state.lifetime_earned, prestigePoints: state.prestige_points, prestigeMultiplier: parseFloat(state.prestige_multiplier), businesses: state.businesses });
            }
            setLoading(false);
        };
        init();
    }, []);

    useEffect(() => {
        const interval = setInterval(() => {
            setGame(prev => {
                let newMoney = prev.money;
                const updatedBusinesses = { ...prev.businesses };
                for (const bConfig of BUSINESSES) {
                    const bState = { ...updatedBusinesses[bConfig.id] };
                    if (bState.owned <= 0) continue;
                    const incomePerTick = calculateIncomePerSecond(bConfig, bState, prev.prestigeMultiplier) / 10;
                    const tickProgress = (100 / (bConfig.timeToEarn / 100));
                    bState.progress += tickProgress;
                    if (bState.progress >= 100) { newMoney += incomePerTick * 10; bState.progress = 0; }
                    updatedBusinesses[bConfig.id] = bState;
                }
                return { ...prev, money: newMoney, totalEarned: prev.totalEarned + (newMoney - prev.money), lifetimeEarned: prev.lifetimeEarned + (newMoney - prev.money), businesses: updatedBusinesses };
            });
        }, 100);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const saveInterval = setInterval(() => { if (vkUser && gameRef.current.lifetimeEarned > 0) saveGameState(vkUser.id, gameRef.current); }, 10000);
        return () => clearInterval(saveInterval);
    }, [vkUser]);

    useEffect(() => { fetchLeaderboard().then(setLeaderboard); }, [game.prestigePoints]);

    const handleBuy = useCallback((id: string) => {
        setGame(prev => {
            const config = BUSINESSES.find(b => b.id === id)!;
            const cost = calculateCost(config, prev.businesses[id].owned);
            if (prev.money < cost) return prev;
            return { ...prev, money: prev.money - cost, businesses: { ...prev.businesses, [id]: { ...prev.businesses[id], owned: prev.businesses[id].owned + 1, progress: 0 } } };
        });
    }, []);

    const handleUpgrade = useCallback((id: string) => {
        setGame(prev => {
            const config = BUSINESSES.find(b => b.id === id)!;
            const cost = calculateCost(config, prev.businesses[id].owned) * 5;
            if (prev.money < cost || prev.businesses[id].owned === 0) return prev;
            return { ...prev, money: prev.money - cost, businesses: { ...prev.businesses, [id]: { ...prev.businesses[id], level: prev.businesses[id].level + 1 } } };
        });
    }, []);

    const handlePrestige = useCallback(() => {
        setGame(prev => {
            const gain = calculatePrestigeGain(prev.lifetimeEarned);
            if (gain <= 0) return prev;
            const newPoints = prev.prestigePoints + gain;
            return { ...getInitialGameState(), prestigePoints: newPoints, prestigeMultiplier: calculatePrestigeMultiplier(newPoints), lifetimeEarned: 0 };
        });
        setActiveModal(null);
    }, []);

    const handleAdBonus = useCallback(() => { setGame(prev => ({ ...prev, money: prev.money + (prev.totalEarned > 1000 ? 1000 : prev.totalEarned) })); }, []);

    const formatMoney = (val: number) => {
        if (val >= 1e12) return `$${(val/1e12).toFixed(2)}T`;
        if (val >= 1e9) return `$${(val/1e9).toFixed(2)}B`;
        if (val >= 1e6) return `$${(val/1e6).toFixed(2)}M`;
        if (val >= 1e3) return `$${(val/1e3).toFixed(2)}K`;
        return `$${Math.floor(val)}`;
    };

    if (loading) return <ScreenSpinner size="large" />;

    return (
        <View activePanel="main" modal={<ModalRoot activeModal={activeModal} onClose={() => setActiveModal(null)}><PrestigePanel lifetimeEarned={game.lifetimeEarned} currentPoints={game.prestigePoints} onPrestige={handlePrestige} onClose={() => setActiveModal(null)} /></ModalRoot>}>
            <Panel id="main">
                <PanelHeader before={<div style={{ paddingLeft: 8, fontSize: 24 }}>🏢</div>} after={<div onClick={() => setActiveModal('prestige')} style={{ cursor: 'pointer', color: 'var(--vkui--color_text_accent)' }}>⭐ {game.prestigePoints}</div>}>Digital Empire</PanelHeader>
                <div style={{ padding: '16px 16px 0', backgroundColor: 'var(--vkui--color_background_content)', borderBottomLeftRadius: 16, borderBottomRightRadius: 16, marginBottom: 16 }}>
                    <Title level="1" style={{ textAlign: 'center', margin: 0 }}>{formatMoney(game.money)}</Title>
                    <div style={{ textAlign: 'center', marginTop: 4, color: 'var(--vkui--color_text_subsecondary)', fontSize: 14 }}>Множитель: x{game.prestigeMultiplier.toFixed(1)}</div>
                    <Monetization onAdWatch={handleAdBonus} />
                </div>
                <div style={{ padding: '0 8px' }}>{BUSINESSES.map(biz => <BusinessCard key={biz.id} config={biz} state={game.businesses[biz.id]} money={game.money} prestigeMult={game.prestigeMultiplier} onBuy={handleBuy} onUpgrade={handleUpgrade} />)}</div>
                <Leaderboard data={leaderboard} />
                <div style={{ height: 50 }} />
            </Panel>
        </View>
    );
};
export default App;"""
}

def create_project():
    for path, content in files.items():
        full_path = os.path.join(PROJECT_NAME, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
    print(f"✅ Проект '{PROJECT_NAME}' успешно создан!")

if __name__ == "__main__":
    create_project()
