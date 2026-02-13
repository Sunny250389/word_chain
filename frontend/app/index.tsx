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
  
  // Animation values - use useRef to persist across renders
  const letterScale = React.useRef(new Animated.Value(1)).current;
  const messageOpacity = React.useRef(new Animated.Value(0)).current;
  const scoreAnimation = React.useRef(new Animated.Value(0)).current;

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
    }
    setLoading(false);
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
    return () => clearInterval(interval);
  }, [isTimerActive, timeLeft, gameState]);

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
    }
    setLoading(false);
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
    }
    setLoading(false);
  };

  // Render welcome screen
  if (!gameState) {
    return (
      <View style={[styles.container, styles.purpleGradient]}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.welcomeContainer}>
            <Text style={styles.title}>Word Chain</Text>
            <Text style={styles.subtitle}>Challenge yourself in this exciting word game!</Text>
            
            {!showTimerSelect ? (
              <>
                <View style={styles.rulesContainer}>
                  <Text style={styles.rulesTitle}>How to Play:</Text>
                  <Text style={styles.ruleText}>• Type a word starting with the given letter</Text>
                  <Text style={styles.ruleText}>• App responds with a word starting with your last letter</Text>
                  <Text style={styles.ruleText}>• Longer & rarer words earn more points (max 10/word)</Text>
                  <Text style={styles.ruleText}>• First to reach 100 points wins!</Text>
                  <Text style={styles.ruleText}>• You can pass if stuck</Text>
                </View>

                <TouchableOpacity
                  style={styles.startButton}
                  onPress={() => setShowTimerSelect(true)}
                  disabled={loading}
                >
                  <Text style={styles.startButtonText}>Start Game</Text>
                </TouchableOpacity>
              </>
            ) : (
              <>
                <View style={styles.timerSelectContainer}>
                  <Text style={styles.timerSelectTitle}>Choose Timer Duration</Text>
                  
                  <TouchableOpacity
                    style={[styles.timerOption, selectedTimer === 0 && styles.timerOptionSelected]}
                    onPress={() => setSelectedTimer(0)}
                  >
                    <Text style={[styles.timerOptionText, selectedTimer === 0 && styles.timerOptionTextSelected]}>
                      No Timer
                    </Text>
                  </TouchableOpacity>
                  
                  <TouchableOpacity
                    style={[styles.timerOption, selectedTimer === 15 && styles.timerOptionSelected]}
                    onPress={() => setSelectedTimer(15)}
                  >
                    <Text style={[styles.timerOptionText, selectedTimer === 15 && styles.timerOptionTextSelected]}>
                      15 seconds
                    </Text>
                  </TouchableOpacity>
                  
                  <TouchableOpacity
                    style={[styles.timerOption, selectedTimer === 30 && styles.timerOptionSelected]}
                    onPress={() => setSelectedTimer(30)}
                  >
                    <Text style={[styles.timerOptionText, selectedTimer === 30 && styles.timerOptionTextSelected]}>
                      30 seconds
                    </Text>
                  </TouchableOpacity>
                  
                  <TouchableOpacity
                    style={[styles.timerOption, selectedTimer === 60 && styles.timerOptionSelected]}
                    onPress={() => setSelectedTimer(60)}
                  >
                    <Text style={[styles.timerOptionText, selectedTimer === 60 && styles.timerOptionTextSelected]}>
                      60 seconds
                    </Text>
                  </TouchableOpacity>
                </View>

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
                      {loading ? 'Starting...' : 'Confirm'}
                    </Text>
                  </TouchableOpacity>
                </View>
              </>
            )}
          </View>
        </SafeAreaView>
      </View>
    );
  }

  // Render game over screen
  if (gameState.status !== 'active') {
    const userWon = gameState.status === 'user_won';
    return (
      <View style={[styles.container, userWon ? styles.greenGradient : styles.redGradient]}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.gameOverContainer}>
            <Text style={styles.gameOverTitle}>
              {userWon ? '🎉 You Win!' : '😊 I Win!'}
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
              onPress={startNewGame}
            >
              <Text style={styles.playAgainButtonText}>Play Again</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </View>
    );
  }

  // Render active game
  return (
    <View style={[styles.container, styles.purpleGradient]}>
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.keyboardView}
        >
          <ScrollView contentContainerStyle={styles.scrollContent}>
            {/* Score Display */}
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
                  <Text style={styles.timerText}>∞</Text>
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
                { transform: [{ scale: letterScale }] },
              ]}
            >
              <Text style={styles.letterText}>{gameState.current_letter}</Text>
              <Text style={styles.letterSubtext}>Start your word with this letter</Text>
            </Animated.View>

            {/* Last Word Display */}
            {gameState.last_word && (
              <View style={styles.lastWordContainer}>
                <Text style={styles.lastWordLabel}>Last word:</Text>
                <Text style={styles.lastWordText}>{gameState.last_word}</Text>
              </View>
            )}

            {/* Message Display */}
            <View style={styles.messageContainerWrapper}>
              {message ? (
                <Animated.View
                  style={[styles.messageContainer, { opacity: messageOpacity }]}
                >
                  <Text style={styles.messageText}>{message}</Text>
                </Animated.View>
              ) : null}
            </View>

            {/* Input Field */}
            <View style={styles.inputContainer}>
              <TextInput
                style={styles.input}
                value={userWord}
                onChangeText={setUserWord}
                placeholder="Type your word here..."
                placeholderTextColor="#999"
                autoCapitalize="none"
                autoCorrect={false}
                editable={!loading}
                onSubmitEditing={handleSubmit}
              />
            </View>

            {/* Action Buttons */}
            <View style={styles.buttonContainer}>
              <TouchableOpacity
                style={[styles.button, styles.submitButton]}
                onPress={handleSubmit}
                disabled={loading || !userWord.trim()}
              >
                <Text style={styles.buttonText}>
                  {loading ? 'Checking...' : 'Submit'}
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.button, styles.passButton]}
                onPress={handlePass}
                disabled={loading}
              >
                <Text style={styles.buttonText}>Pass</Text>
              </TouchableOpacity>
            </View>

            {/* Used Words List */}
            <View style={styles.usedWordsContainer}>
              <Text style={styles.usedWordsTitle}>Used Words ({gameState.used_words.length})</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                <View style={styles.usedWordsList}>
                  {gameState.used_words.slice().reverse().map((word, index) => (
                    <View key={index} style={styles.usedWordChip}>
                      <Text style={styles.usedWordText}>{word}</Text>
                    </View>
                  ))}
                </View>
              </ScrollView>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  purpleGradient: {
    backgroundColor: '#764ba2',
  },
  greenGradient: {
    backgroundColor: '#11998e',
  },
  redGradient: {
    backgroundColor: '#ee0979',
  },
  safeArea: {
    flex: 1,
  },
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    padding: 20,
  },
  welcomeContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  title: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 10,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 18,
    color: '#fff',
    marginBottom: 40,
    textAlign: 'center',
  },
  rulesContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 20,
    padding: 24,
    marginBottom: 40,
    width: '100%',
  },
  rulesTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
  },
  ruleText: {
    fontSize: 16,
    color: '#fff',
    marginBottom: 8,
    lineHeight: 24,
  },
  startButton: {
    backgroundColor: '#fff',
    paddingHorizontal: 48,
    paddingVertical: 16,
    borderRadius: 30,
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
  },
  startButtonText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#667eea',
  },
  scoreContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 30,
  },
  scoreBox: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 15,
    padding: 16,
    minWidth: 100,
    alignItems: 'center',
  },
  scoreLabel: {
    fontSize: 14,
    color: '#fff',
    marginBottom: 4,
  },
  scoreValue: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
  },
  timerBox: {
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderRadius: 30,
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  timerText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  letterContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 30,
    padding: 40,
    alignItems: 'center',
    marginBottom: 20,
    elevation: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
  },
  letterText: {
    fontSize: 80,
    fontWeight: 'bold',
    color: '#667eea',
  },
  letterSubtext: {
    fontSize: 14,
    color: '#666',
    marginTop: 8,
  },
  lastWordContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 15,
    padding: 12,
    marginBottom: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  lastWordLabel: {
    fontSize: 14,
    color: '#fff',
    marginRight: 8,
  },
  lastWordText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  messageContainerWrapper: {
    minHeight: 64,
    marginBottom: 16,
    justifyContent: 'center',
  },
  messageContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 15,
    padding: 16,
  },
  messageText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    textAlign: 'center',
  },
  inputContainer: {
    marginBottom: 20,
  },
  input: {
    backgroundColor: '#fff',
    borderRadius: 15,
    padding: 16,
    fontSize: 18,
    color: '#333',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 30,
    gap: 12,
  },
  button: {
    flex: 1,
    paddingVertical: 16,
    borderRadius: 15,
    alignItems: 'center',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
  },
  submitButton: {
    backgroundColor: '#38ef7d',
  },
  passButton: {
    backgroundColor: '#ff6b6b',
  },
  buttonText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  usedWordsContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 15,
    padding: 16,
  },
  usedWordsTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 12,
  },
  usedWordsList: {
    flexDirection: 'row',
    gap: 8,
  },
  usedWordChip: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  usedWordText: {
    fontSize: 14,
    color: '#667eea',
    fontWeight: '600',
  },
  gameOverContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  gameOverTitle: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 40,
    textAlign: 'center',
  },
  finalScoreContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    width: '100%',
    marginBottom: 30,
  },
  finalScoreBox: {
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderRadius: 20,
    padding: 24,
    minWidth: 120,
    alignItems: 'center',
  },
  finalScoreLabel: {
    fontSize: 16,
    color: '#fff',
    marginBottom: 8,
  },
  finalScore: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#fff',
  },
  totalWordsText: {
    fontSize: 18,
    color: '#fff',
    marginBottom: 40,
  },
  playAgainButton: {
    backgroundColor: '#fff',
    paddingHorizontal: 48,
    paddingVertical: 16,
    borderRadius: 30,
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
  },
  playAgainButtonText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#11998e',
  },
  timerSelectContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 20,
    padding: 24,
    marginBottom: 30,
    width: '100%',
  },
  timerSelectTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 20,
    textAlign: 'center',
  },
  timerOption: {
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderRadius: 15,
    padding: 16,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  timerOptionSelected: {
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
    borderColor: '#fff',
  },
  timerOptionText: {
    fontSize: 18,
    color: '#fff',
    textAlign: 'center',
  },
  timerOptionTextSelected: {
    fontWeight: 'bold',
  },
  timerButtonsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  backButton: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 25,
  },
  backButtonText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
  },
  confirmButton: {
    flex: 1,
    backgroundColor: '#fff',
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 25,
  },
  confirmButtonText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#764ba2',
    textAlign: 'center',
    numberOfLines: 1,
  },
});
