import React, { useState, useEffect } from 'react';
import { AppShell, Container, Title, Group, Button, Tabs, Image, SimpleGrid, Badge, Card, Text, Stack, Alert, Loader, Notification } from '@mantine/core';
import { IconChartBar, IconArrowLeft, IconRefresh, IconCheck, IconX, IconAlertCircle } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_URL = "http://localhost:8000/api";
const PLOTS_URL = "http://localhost:8000/plots";

export default function AnalyticsPanel() {
    const navigate = useNavigate();
    const [status, setStatus] = useState({ fedavg: false, fedprox: false, comparison: false });
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [refreshKey, setRefreshKey] = useState(Date.now()); // Force image reload

    const fetchStatus = async () => {
        try {
            const res = await axios.get(`${API_URL}/analytics/status`);
            setStatus(res.data);
        } catch (e) {
            console.error("Failed to fetch status", e);
        }
    };

    useEffect(() => {
        fetchStatus();
    }, []);

    const generatePlots = async () => {
        setGenerating(true);
        try {
            await axios.post(`${API_URL}/generate_plots`);
            setRefreshKey(Date.now());
            await fetchStatus();
        } catch (e) {
            console.error(e);
        } finally {
            setGenerating(false);
        }
    };

    return (
        <AppShell header={{ height: 60 }} padding="md">
            <AppShell.Header>
                <Group h="100%" px="md" justify="space-between">
                    <Group>
                        <Button variant="subtle" leftSection={<IconArrowLeft />} onClick={() => navigate('/lab')}>Back to Lab</Button>
                        <Title order={3}>Analytics Dashboard</Title>
                    </Group>
                    <Button
                        leftSection={generating ? <Loader size="xs" color="white" /> : <IconRefresh />}
                        onClick={generatePlots}
                        disabled={generating}
                    >
                        {generating ? "Generating..." : "Refresh Plots"}
                    </Button>
                </Group>
            </AppShell.Header>

            <AppShell.Main>
                <Container size="xl">
                    <SimpleGrid cols={3} mb="xl">
                        <StatusCard title="FedAvg (Baseline)" ready={status.fedavg} />
                        <StatusCard title="FedProx (Adaptation)" ready={status.fedprox} />
                        <StatusCard title="Comparison" ready={status.comparison} />
                    </SimpleGrid>

                    <Tabs defaultValue="fedavg" variant="outline" radius="md">
                        <Tabs.List mb="md">
                            <Tabs.Tab value="fedavg" disabled={!status.fedavg} leftSection={<IconChartBar size={16} />}>
                                FedAvg Results
                            </Tabs.Tab>
                            <Tabs.Tab value="fedprox" disabled={!status.fedprox} leftSection={<IconChartBar size={16} />}>
                                FedProx Results
                            </Tabs.Tab>
                            <Tabs.Tab value="comparison" disabled={!status.comparison} color="purple" leftSection={<IconChartBar size={16} />}>
                                Comparative Analysis
                            </Tabs.Tab>
                        </Tabs.List>

                        <Tabs.Panel value="fedavg">
                            <PlotGallery algo="fedavg" refreshKey={refreshKey} />
                        </Tabs.Panel>

                        <Tabs.Panel value="fedprox">
                            <PlotGallery algo="fedprox" refreshKey={refreshKey} />
                        </Tabs.Panel>

                        <Tabs.Panel value="comparison">
                            <ComparisonGallery refreshKey={refreshKey} />
                        </Tabs.Panel>
                    </Tabs>
                </Container>
            </AppShell.Main>
        </AppShell>
    );
}

function StatusCard({ title, ready }) {
    return (
        <Card withBorder padding="sm" radius="md">
            <Group justify="space-between">
                <Text fw={500}>{title}</Text>
                <Badge color={ready ? "green" : "gray"} variant="light">
                    {ready ? "Available" : "Not Run"}
                </Badge>
            </Group>
        </Card>
    );
}

function PlotGallery({ algo, refreshKey }) {
    const metrics = ['accuracy', 'loss', 'precision', 'recall', 'f1'];
    return (
        <Stack gap="xl">
            <SimpleGrid cols={2}>
                {metrics.map(m => (
                    <Card key={m} withBorder padding="xs" radius="md">
                        <Text ta="center" size="sm" tt="uppercase" c="dimmed" mb="xs">{m}</Text>
                        <Image
                            src={`${PLOTS_URL}/${algo}/${m}.png?t=${refreshKey}`}
                            fallbackSrc="https://placehold.co/600x400?text=Plot+Not+Found"
                            radius="sm"
                        />
                    </Card>
                ))}
                <Card withBorder padding="xs" radius="md">
                    <Text ta="center" size="sm" tt="uppercase" c="dimmed" mb="xs">Confusion Matrix</Text>
                    <Image
                        src={`${PLOTS_URL}/${algo}/confusion_matrix.png?t=${refreshKey}`}
                        fallbackSrc="https://placehold.co/600x400?text=Matrix+Not+Found"
                        radius="sm"
                    />
                </Card>
            </SimpleGrid>
        </Stack>
    );
}

function ComparisonGallery({ refreshKey }) {
    const metrics = ['accuracy', 'loss', 'precision', 'recall', 'f1'];
    return (
        <Stack gap="xl">
            <SimpleGrid cols={2}>
                {metrics.map(m => (
                    <Card key={m} withBorder padding="xs" radius="md">
                        <Text ta="center" size="sm" tt="uppercase" c="dimmed" mb="xs">{m} Comparison</Text>
                        <Image
                            src={`${PLOTS_URL}/comparison/compare_${m}.png?t=${refreshKey}`}
                            fallbackSrc="https://placehold.co/600x400?text=Comparison+Not+Generated"
                            radius="sm"
                        />
                    </Card>
                ))}
            </SimpleGrid>
        </Stack>
    );
}
