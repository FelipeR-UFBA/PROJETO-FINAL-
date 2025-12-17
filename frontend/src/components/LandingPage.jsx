
import React from 'react';
import { Container, Title, Text, Button, Group, Stack, ThemeIcon, SimpleGrid, Card, rem, Center } from '@mantine/core';
import { IconShieldLock, IconBrain, IconNetwork, IconArrowRight } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

export default function LandingPage() {
    const navigate = useNavigate();

    return (
        <Center h="100vh" w="100vw" style={{ overflow: 'hidden' }}>
            <Container size="lg">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
                    <Stack align="center" gap="lg" mb={50}>
                        <ThemeIcon size={80} radius="xl" variant="gradient" gradient={{ from: 'blue', to: 'cyan' }}>
                            <IconShieldLock style={{ width: rem(50), height: rem(50) }} />
                        </ThemeIcon>
                        <Title ta="center" order={1} style={{ fontSize: rem(48), fontWeight: 900 }}>
                            Federated IDS Network
                        </Title>
                        <Text c="dimmed" ta="center" size="xl" maw={600}>
                            A next-generation Intrusion Detection System powered by Multi-Agent BDI Architectures and Federated Learning.
                        </Text>

                        <Button
                            size="xl"
                            rightSection={<IconArrowRight />}
                            variant="gradient"
                            gradient={{ from: 'blue', to: 'cyan' }}
                            onClick={() => navigate('/lab')}
                        >
                            Enter Control Lab
                        </Button>
                    </Stack>
                </motion.div>

                <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="xl" mt={50}>
                    <FeatureCard
                        icon={IconNetwork}
                        title="Multi-Agent System"
                        description="Autonomous BDI agents (SPADE) collaborate to defend the network without central points of failure."
                        delay={0.2}
                    />
                    <FeatureCard
                        icon={IconBrain}
                        title="Federated Learning"
                        description="Privacy-preserving AI (Flower) trains on local data. Only insights are shared, never raw packets."
                        delay={0.4}
                    />
                    <FeatureCard
                        icon={IconShieldLock}
                        title="NSL-KDD Defense"
                        description="Benchmarked against the NSL-KDD dataset, demonstrating robust generalization against unseen attacks."
                        delay={0.6}
                    />
                </SimpleGrid>
            </Container>
        </Center>
    );
}

function FeatureCard({ icon: Icon, title, description, delay }) {
    return (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay, duration: 0.5 }}>
            <Card shadow="sm" padding="lg" radius="md" withBorder>
                <Card.Section withBorder inheritPadding py="xs">
                    <Group justify="space-between">
                        <Text fw={500}>{title}</Text>
                        <ThemeIcon variant="light" color="cyan">
                            <Icon style={{ width: rem(20), height: rem(20) }} />
                        </ThemeIcon>
                    </Group>
                </Card.Section>
                <Text mt="sm" c="dimmed" size="sm">
                    {description}
                </Text>
            </Card>
        </motion.div>
    );
}
