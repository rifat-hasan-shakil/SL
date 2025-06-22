number_guess_game <- function() {
  cat("🎲 Welcome to the Number Guessing Game!\n")
  cat("I'm thinking of a number between 1 and 100...\n")

  target <- sample(1:100, 1)
  guess <- NA
  attempts <- 0

  while (guess != target) {
    guess <- as.numeric(readline(prompt = "Enter your guess: "))
    
    if (is.na(guess)) {
      cat("Please enter a valid number.\n")
      next
    }

    attempts <- attempts + 1

    if (guess < target) {
      cat("🔼 Too low! Try a higher number.\n")
    } else if (guess > target) {
      cat("🔽 Too high! Try a lower number.\n")
    } else {
      cat(sprintf("🎉 Congratulations! You guessed the number in %d attempts.\n", attempts))
    }
  }
}

# Start the game
number_guess_game()
