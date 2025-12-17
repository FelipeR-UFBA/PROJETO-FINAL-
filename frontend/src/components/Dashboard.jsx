import React, { useState, useEffect, useRef } from 'react';
import { AppShell, Burger, Group, Title, Button, Text, Code, Paper, SimpleGrid, Card, RingProgress, Stack, Center, Select, ScrollArea, Badge } from '@mantine/core';
import { IconPlayerPlay, IconCpu, IconServer, IconInfoCircle, IconBolt, IconShieldLock, IconPlus, IconChartDots } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { notifications } from '@mantine/notifications';
import axios from 'axios';

const API_URL = "http://localhost:8000/api";

export default function Dashboard() {
    const navigate = useNavigate();
    const [activeAgents, setActiveAgents] = useState(0);
    const [logs, setLogs] = useState([]);
    const [metrics, setMetrics] = useState([]);
    const [round, setRound] = useState(0);
    const [algo, setAlgo] = useState("fedprox");
    const logEndRef = useRef(null);

    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs]);

    useEffect(() => {
        axios.get(`${API_URL}/get_algorithm`)
            .then(res => setAlgo(res.data.algorithm))
            .catch(err => console.error(err));
    }, []);

    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                const res = await axios.get(`${API_URL}/status`);
                setActiveAgents(res.data.active_agents);
            } catch (e) {
                // silent fail
            }
        }, 2000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const ws = new WebSocket("ws://localhost:8000/ws");

        ws.onopen = () => {
            addLog("System Uplink Established (WebSocket).");
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                if (message.type === "metrics_update") {
                    const data = message.data;
                    setMetrics(data);

                    if (data.length > 0) {
                        const last = data[data.length - 1];
                        setRound(last.round);
                    }
                } else if (message.type === "log") {
                    setLogs(prev => [...prev.slice(-30), message.data]);
                }
            } catch (e) {
                console.error("WS Parse Error", e);
            }
        };

        ws.onclose = () => {
            addLog("System Uplink Lost. Reconnecting...");
        };

        return () => ws.close();
    }, []);

    const addLog = (msg) => {
        setLogs(prev => [...prev.slice(-15), `[${new Date().toLocaleTimeString()}] ${msg}`]);
    };

    const handleAlgoChange = async (value) => {
        if (!value) return;
        setAlgo(value);
        try {
            await axios.post(`${API_URL}/set_algorithm`, { algorithm: value });
            addLog(`Algorithm Switched to: ${value.toUpperCase()}`);
            notifications.show({ title: 'System', message: `Algorithm set to ${value.toUpperCase()}`, color: 'blue' });
            addLog(`Algorithm Switched to: ${value.toUpperCase()}`);
            notifications.show({ title: 'System', message: `Algorithm set to ${value.toUpperCase()}`, color: 'blue' });
            setMetrics([]);
        } catch (e) {
            notifications.show({ title: 'Error', message: 'Failed to switch algorithm', color: 'red' });
        }
    };

    const startInfra = async () => {
        try {
            await axios.post(`${API_URL}/start_infrastructure`);
            addLog("Infrastructure Initialization: SPADE & Flower Server Starting...");
            notifications.show({ title: 'System', message: 'Infrastructure Started', color: 'green' });
        } catch (e) {
            notifications.show({ title: 'Error', message: 'Failed to start infra', color: 'red' });
        }
    };

    const addAgent = async () => {
        try {
            const res = await axios.post(`${API_URL}/add_agent`);
            addLog(`New Agent Deployed: Client-${res.data.cid}`);
            notifications.show({ title: 'Agent', message: `Agent ${res.data.cid} Added`, color: 'blue' });
        } catch (e) {
            notifications.show({ title: 'Error', message: 'Failed to add agent', color: 'red' });
        }
    };

    const startFL = async () => {
        try {
            await axios.post(`${API_URL}/start_federation`);
            addLog("Federation Protocol Initiated via Agent Communication (XMPP)...");
            notifications.show({ title: 'Federation', message: 'Agents Activated', color: 'teal' });
        } catch (e) {
            notifications.show({ title: 'Error', message: 'Failed to start FL', color: 'red' });
        }
    };

    const handleResetSystem = async () => {
        try {
            await axios.post(`${API_URL}/reset_system`);
            addLog("SYSTEM RESET: All data wiped. Ready for fresh experiment.");
            notifications.show({ title: 'System Reset', message: 'All data cleared. Ready for fresh start.', color: 'red' });
            setMetrics([]);
            setRound(0);
            setTimeout(() => window.location.reload(), 1500);
        } catch (e) {
            notifications.show({ title: 'Error', message: 'Failed to reset system', color: 'red' });
        }
    };



    const renderConfusionMatrix = (matrix) => {
        if (!matrix) return <Text c="dimmed">Waiting for data...</Text>;
        return (
            <Paper withBorder p="xs" style={{ background: '#1A1B1E' }}>
                <Group grow>
                    <Stack align="center" gap={0}>
                        <Text size="xs" c="dimmed">TN</Text>
                        <Text fw={700} c="green">{matrix[0][0]}</Text>
                    </Stack>
                    <Stack align="center" gap={0}>
                        <Text size="xs" c="dimmed">FP</Text>
                        <Text fw={700} c="red">{matrix[0][1]}</Text>
                    </Stack>
                </Group>
                <Group grow mt="xs">
                    <Stack align="center" gap={0}>
                        <Text size="xs" c="dimmed">FN</Text>
                        <Text fw={700} c="red">{matrix[1][0]}</Text>
                    </Stack>
                    <Stack align="center" gap={0}>
                        <Text size="xs" c="dimmed">TP</Text>
                        <Text fw={700} c="green">{matrix[1][1]}</Text>
                    </Stack>
                </Group>
            </Paper>
        );
    };

    const lastMetric = metrics.length > 0 ? metrics[metrics.length - 1] : null;

    return (
        <AppShell padding="md" header={{ height: 60 }}>
            <AppShell.Header>
                <Group h="100%" px="md" justify="space-between">
                    <Group>
                        <IconServer size={30} />
                        <Title order={3}>IDS Command Center</Title>
                    </Group>
                    <Group>
                        <Button variant="outline" leftSection={<IconChartDots />} onClick={() => navigate('/analytics')}>Analytics & Results</Button>
                        <Button variant="light" color="red" onClick={handleResetSystem}>Reset System</Button>
                    </Group>
                </Group>
            </AppShell.Header>

            <AppShell.Main>
                <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg">

                    <Paper p="md" radius="md" withBorder>
                        <Title order={4} mb="md">Operations</Title>
                        <Stack>
                            <Select
                                label="Learning Algorithm"
                                data={[
                                    { value: 'fedavg', label: 'FedAvg (Baseline)' },
                                    { value: 'fedprox', label: 'FedProx (Domain Adaptation)' }
                                ]}
                                value={algo}
                                onChange={handleAlgoChange}
                                mb="sm"
                            />
                            <Button leftSection={<IconCpu />} onClick={startInfra} variant="light">1. Start Infrastructure</Button>
                            <Button leftSection={<IconPlus />} onClick={addAgent} variant="outline">2. Add Agent Node</Button>
                            <Button leftSection={<IconPlayerPlay />} onClick={startFL} color="green">3. Start Federation</Button>
                        </Stack>
                    </Paper>

                    <Paper p="md" radius="md" withBorder>
                        <Title order={4} mb="md">Performance (Real-Time)</Title>
                        <div style={{ height: 200 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={metrics}>
                                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                    <XAxis dataKey="round" />
                                    <YAxis domain={[0, 1]} />
                                    <Tooltip contentStyle={{ backgroundColor: '#333' }} />
                                    <Line type="monotone" dataKey="accuracy" stroke="#228be6" name="Accuracy" strokeWidth={2} dot={{ r: 3 }} />
                                    <Line type="monotone" dataKey="f1" stroke="#40c057" name="F1 Score" strokeWidth={2} dot={false} />
                                    <Line type="monotone" dataKey="recall" stroke="#fab005" name="Recall" strokeWidth={2} dot={false} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>

                        <SimpleGrid cols={2} mt="md">
                            <Paper withBorder p="xs">
                                <Text size="xs" c="dimmed">Global Accuracy</Text>
                                <Text fw={700} size="lg">{lastMetric ? (lastMetric.accuracy * 100).toFixed(2) : 0}%</Text>
                            </Paper>
                            <Paper withBorder p="xs">
                                <Text size="xs" c="dimmed">F1 Score</Text>
                                <Text fw={700} size="lg" c="green">{lastMetric ? lastMetric.f1.toFixed(3) : 0}</Text>
                            </Paper>
                            <Paper withBorder p="xs">
                                <Text size="xs" c="dimmed">Precision</Text>
                                <Text fw={700} size="lg">{lastMetric ? lastMetric.precision.toFixed(3) : 0}</Text>
                            </Paper>
                            <Paper withBorder p="xs">
                                <Text size="xs" c="dimmed">Recall</Text>
                                <Text fw={700} size="lg">{lastMetric ? lastMetric.recall.toFixed(3) : 0}</Text>
                            </Paper>
                        </SimpleGrid>

                        <Title order={5} mt="md" mb="xs">Confusion Matrix</Title>
                        {lastMetric && renderConfusionMatrix(lastMetric.confusion_matrix)}

                    </Paper>

                    <Paper p="md" radius="md" withBorder bg="dark.8">
                        <Title order={4} mb="md" c="white">System Terminal</Title>
                        <Code block style={{ height: 600, overflowY: 'auto' }} c="green.4">
                            {logs.map((l, i) => (
                                <div key={i}>{l}</div>
                            ))}
                            {logs.length === 0 && <Text c="dimmed">// Waiting for system start...</Text>}
                        </Code>
                    </Paper>

                </SimpleGrid>
            </AppShell.Main>
        </AppShell>
    );
}
