import React, { useState, useEffect, useCallback } from 'react';

import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  Animated,
  Dimensions,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';

import { Ionicons } from '@expo/vector-icons';

import AsyncStorage from '@react-native-async-storage/async-storage';

const EXPO_PUBLIC_BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

const { width } = Dimensions.get('window');

interface GameState {
  game_id: string;
  current_letter: string;
  user_score: number;
  app_score: number;
  used_words: string[];
  turn: string;
  status: string;
  time_limit: number;
  last_word: string | null;
}

export default function Index() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [userWord, setUserWord] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [timeLeft, setTimeLeft] = useState(30);
  const [isTimerActive, setIsTimerActive] = useState(false);
  const [selectedTimer, setSelectedTimer] = useState(30);
  const [showTimerSelect, setShowTimerSelect] = useState(false);
  const [userId, setUserId] = useState('');
  const [stats, setStats] = useState({
    total_games: 0,
    wins: 0,
    losses: 0,
    win_rate: 0,
  });

  // Animation values - use useRef to persist across renders
  const letterScale = React.useRef(new Animated.Value(1)).current;
  const messageOpacity = React.useRef(new Animated.Value(0)).current;
  const scoreAnimation = React.useRef(new Animated.Value(0)).current;

  // Initialize user ID and load stats
  useEffect(() => {
    initializeUser();
  }, []);

  const initializeUser = async () => {
    try {
      let storedUserId = await AsyncStorage.getItem('userId');
      if (!storedUserId) {
        // Generate new user ID
        storedUserId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        await AsyncStorage.setItem('userId', storedUserId);
      }
      setUserId(storedUserId);
      await loadStats(storedUserId);
    } catch (error) {
      console.error('Failed to initialize user:', error);
    }
  };

  const loadStats = async (uid: string) => {
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/stats/${uid}`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const updateStats = async (won: boolean) => {
    if (!userId) return;
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/stats/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, won }),
      });
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to update stats:', error);
    }
  };

  // Start new game
  const startNewGame = async (timerDuration: number) => {
    setLoading(true);
    setMessage('');
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/game/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ time_limit: timerDuration }),
      });
      const data = await response.json();
      setGameState(data);
      setTimeLeft(timerDuration);
      setIsTimerActive(timerDuration > 0);
      setShowTimerSelect(false);
      animateLetter();
    } catch (error) {
      setMessage('Failed to start game. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Animate letter
  const animateLetter = () => {
    Animated.sequence([
      Animated.spring(letterScale, {
        toValue: 1.3,
        friction: 3,
        useNativeDriver: true,
      }),
      Animated.spring(letterScale, {
        toValue: 1,
        friction: 3,
        useNativeDriver: true,
      }),
    ]).start();
  };

  // Show message with animation
  const showMessage = (msg: string) => {
    setMessage(msg);
    // Reset opacity first
    messageOpacity.setValue(0);
    Animated.sequence([
      Animated.timing(messageOpacity, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.delay(3000),
      Animated.timing(messageOpacity, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }),
    ]).start(() => setMessage(''));
  };

  // Timer countdown
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isTimerActive && timeLeft > 0 && gameState?.status === 'active') {
      interval = setInterval(() => {
        setTimeLeft((prev) => prev - 1);
      }, 1000);
    } else if (timeLeft === 0 && gameState?.status === 'active' && isTimerActive) {
      handlePass();
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isTimerActive, timeLeft, gameState]);

  // ✅ Game-over effect moved to top level and conditioned inside
  useEffect(() => {
    if (!gameState) return;
    if (gameState.status === 'active') return;

    const userWon = gameState.status === 'user_won';
    updateStats(userWon);
  }, [gameState]);

  // Submit word
  const handleSubmit = async () => {
    if (!userWord.trim() || !gameState) return;
    setLoading(true);
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/game/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameState.game_id,
          word: userWord.trim(),
        }),
      });
      const data = await response.json();
      if (data.valid) {
        setGameState(data.game_state);
        setUserWord('');
        setTimeLeft(gameState.time_limit);
        showMessage(data.message);
        animateLetter();
      } else {
        showMessage(data.message);
      }
    } catch (error) {
      showMessage('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Pass turn
  const handlePass = async () => {
    if (!gameState) return;
    setLoading(true);
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/game/pass`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameState.game_id }),
      });
      const data = await response.json();
      setGameState(data.game_state);
      setUserWord('');
      setTimeLeft(gameState.time_limit);
      showMessage(data.message);
      animateLetter();
    } catch (error) {
      showMessage('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Exit game
  const handleExit = () => {
    setGameState(null);
    setUserWord('');
    setMessage('');
    setTimeLeft(30);
    setIsTimerActive(false);
    setShowTimerSelect(false);
  };

  // Render welcome screen
  if (!gameState) {
    return (
      <SafeAreaView style={[styles.container, styles.purpleGradient]}>
        <KeyboardAvoidingView
          style={styles.keyboardView}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <ScrollView contentContainerStyle={styles.scrollContent}>
            <View style={styles.welcomeContainer}>
              <Text style={styles.title}>Word Chain</Text>
              <Text style={styles.subtitle}>
                Challenge yourself in this exciting word game!
              </Text>

              {/* Statistics Display */}
              {stats.total_games > 0 && (
                <View style={styles.statsContainer}>
                  <Text style={styles.statsTitle}>Your Stats</Text>
                  <View style={styles.statsRow}>
                    <View style={styles.statItem}>
                      <Text style={styles.statValue}>{stats.wins}</Text>
                      <Text style={styles.statLabel}>Wins</Text>
                    </View>
                    <View style={styles.statItem}>
                      <Text style={styles.statValue}>{stats.total_games}</Text>
                      <Text style={styles.statLabel}>Games</Text>
                    </View>
                    <View style={styles.statItem}>
                      <Text style={styles.statValue}>{stats.win_rate}%</Text>
                      <Text style={styles.statLabel}>Win Rate</Text>
                    </View>
                  </View>
                </View>
              )}

              {!showTimerSelect ? (
                <>
                  <View style={styles.rulesContainer}>
                    <Text style={styles.rulesTitle}>How to Play:</Text>
                    <Text style={styles.ruleText}>
                      • Type a word starting with the given letter
                    </Text>
                    <Text style={styles.ruleText}>
                      • App responds with a word starting with your last letter
                    </Text>
                    <Text style={styles.ruleText}>
                      • Longer & rarer words earn more points (max 10/word)
                    </Text>
                    <Text style={styles.ruleText}>
                      • First to reach 100 points wins!
                    </Text>
                    <Text style={styles.ruleText}>
                      • You can pass if stuck
                    </Text>
                  </View>

                  <TouchableOpacity
                    style={styles.startButton}
                    onPress={() => setShowTimerSelect(true)}
                    disabled={loading}
                  >
                    <Text style={styles.startButtonText}>
                      {loading ? 'Loading...' : 'Start Game'}
                    </Text>
                  </TouchableOpacity>
                </>
              ) : (
                <View style={styles.timerSelectContainer}>
                  <Text style={styles.timerSelectTitle}>Choose Timer Duration</Text>

                  <TouchableOpacity
                    style={[
                      styles.timerOption,
                      selectedTimer === 0 && styles.timerOptionSelected,
                    ]}
                    onPress={() => setSelectedTimer(0)}
                  >
                    <Text
                      style={[
                        styles.timerOptionText,
                        selectedTimer === 0 && styles.timerOptionTextSelected,
                      ]}
                    >
                      No Timer
                    </Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={[
                      styles.timerOption,
                      selectedTimer === 15 && styles.timerOptionSelected,
                    ]}
                    onPress={() => setSelectedTimer(15)}
                  >
                    <Text
                      style={[
                        styles.timerOptionText,
                        selectedTimer === 15 && styles.timerOptionTextSelected,
                      ]}
                    >
                      15 seconds
                    </Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={[
                      styles.timerOption,
                      selectedTimer === 30 && styles.timerOptionSelected,
                    ]}
                    onPress={() => setSelectedTimer(30)}
                  >
                    <Text
                      style={[
                        styles.timerOptionText,
                        selectedTimer === 30 && styles.timerOptionTextSelected,
                      ]}
                    >
                      30 seconds
                    </Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={[
                      styles.timerOption,
                      selectedTimer === 60 && styles.timerOptionSelected,
                    ]}
                    onPress={() => setSelectedTimer(60)}
                  >
                    <Text
                      style={[
                        styles.timerOptionText,
                        selectedTimer === 60 && styles.timerOptionTextSelected,
                      ]}
                    >
                      60 seconds
                    </Text>
                  </TouchableOpacity>

                  <View style={styles.timerButtonsContainer}>
                    <TouchableOpacity
                      style={styles.backButton}
                      onPress={() => setShowTimerSelect(false)}
                    >
                      <Text style={styles.backButtonText}>Back</Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={styles.confirmButton}
                      onPress={() => startNewGame(selectedTimer)}
                      disabled={loading}
                    >
                      <Text style={styles.confirmButtonText}>
                        {loading ? 'Starting...' : 'Start'}
                      </Text>
                    </TouchableOpacity>
                  </View>
                </View>
              )}
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    );
  }

  // Render game over screen
  if (gameState.status !== 'active') {
    const userWon = gameState.status === 'user_won';

    return (
      <SafeAreaView
        style={[
          styles.container,
          userWon ? styles.greenGradient : styles.redGradient,
        ]}
      >
        <View style={styles.gameOverContainer}>
          <Text style={styles.gameOverTitle}>
            {userWon ? 'You Win!' : 'I Win!'}
          </Text>

          <View style={styles.finalScoreContainer}>
            <View style={styles.finalScoreBox}>
              <Text style={styles.finalScoreLabel}>Your Score</Text>
              <Text style={styles.finalScore}>{gameState.user_score}</Text>
            </View>
            <View style={styles.finalScoreBox}>
              <Text style={styles.finalScoreLabel}>App Score</Text>
              <Text style={styles.finalScore}>{gameState.app_score}</Text>
            </View>
          </View>

          <Text style={styles.totalWordsText}>
            Total words played: {gameState.used_words.length}
          </Text>

          <TouchableOpacity
            style={styles.playAgainButton}
            onPress={() => {
              setShowTimerSelect(true);
              setGameState(null);
            }}
          >
            <Text style={styles.playAgainButtonText}>Play Again</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // Render active game
  return (
    <SafeAreaView style={[styles.container, styles.purpleGradient]}>
      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.scoreContainer}>
            <View style={styles.scoreBox}>
              <Text style={styles.scoreLabel}>You</Text>
              <Text style={styles.scoreValue}>{gameState.user_score}</Text>
            </View>

            {gameState.time_limit > 0 ? (
              <View style={styles.timerBox}>
                <Text style={styles.timerText}>{timeLeft}s</Text>
              </View>
            ) : (
              <View style={styles.timerBox}>
                <Text style={styles.timerText}>No Timer</Text>
              </View>
            )}

            <View style={styles.scoreBox}>
              <Text style={styles.scoreLabel}>App</Text>
              <Text style={styles.scoreValue}>{gameState.app_score}</Text>
            </View>
          </View>

          {/* Current Letter Display */}
          <Animated.View
            style={[
              styles.letterContainer,
              {
                transform: [{ scale: letterScale }],
              },
            ]}
          >
            <Text style={styles.letterText}>{gameState.current_letter}</Text>
            <Text sty
