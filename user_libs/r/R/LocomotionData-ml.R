#' Machine Learning and Dimensionality Reduction for Biomechanical Data
#'
#' Created: 2025-06-19 with user permission
#' Purpose: Advanced machine learning and dimensionality reduction capabilities
#'
#' Intent:
#' This module provides comprehensive machine learning functionality specifically designed 
#' for biomechanical locomotion data analysis. It includes dimensionality reduction 
#' techniques (PCA, t-SNE, UMAP), clustering algorithms (k-means, hierarchical), 
#' classification methods (SVM, random forest), and complete machine learning workflows 
#' with cross-validation and hyperparameter tuning.
#'
#' Key Features:
#' - Principal Component Analysis (PCA) for linear dimensionality reduction
#' - t-SNE and UMAP for non-linear dimensionality reduction and visualization
#' - K-means and hierarchical clustering for pattern identification
#' - Support Vector Machines and Random Forest for classification
#' - Cross-validation frameworks with performance metrics
#' - Feature selection and importance analysis
#' - Hyperparameter tuning with grid search
#' - Model evaluation and comparison tools

# Required packages
required_packages <- c("randomForest", "e1071", "cluster", "factoextra", "corrplot")
optional_packages <- c("Rtsne", "umap", "caret", "pROC", "ROCR")

# Check required packages
for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop(paste("Package", pkg, "needed for machine learning analysis. Please install it with: install.packages('", pkg, "')", sep = ""))
  }
}

# Check optional packages and warn if missing
for (pkg in optional_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    warning(paste("Package", pkg, "recommended for enhanced functionality. Install with: install.packages('", pkg, "')", sep = ""))
  }
}

library(stats)
library(cluster)
library(randomForest)
library(e1071)

#' Prepare Data for Machine Learning
#'
#' Extracts and prepares biomechanical data for machine learning analysis
#'
#' @param loco_data LocomotionData object
#' @param subjects Character vector, subjects to include (NULL for all)
#' @param tasks Character vector, tasks to include (NULL for all)
#' @param features Character vector, features to include (NULL for all)
#' @param summary_type Character, "mean", "rom", "full_cycle", or "peak_values"
#' @param normalize Logical, whether to normalize features (default: TRUE)
#' @param remove_na Logical, whether to remove rows with missing values (default: TRUE)
#' @return List containing feature matrix, labels, and metadata
#'
#' @export
prepare_ml_data <- function(loco_data, subjects = NULL, tasks = NULL, features = NULL,
                           summary_type = "mean", normalize = TRUE, remove_na = TRUE) {
  
  # Validate inputs
  if (!is(loco_data, "LocomotionData")) {
    stop("Input must be a LocomotionData object")
  }
  
  # Get defaults if not specified
  if (is.null(subjects)) subjects <- get_subjects(loco_data)
  if (is.null(tasks)) tasks <- get_tasks(loco_data)
  if (is.null(features)) features <- get_features(loco_data)
  
  # Initialize storage
  feature_matrix <- c()
  subject_labels <- c()
  task_labels <- c()
  row_metadata <- list()
  
  for (i in seq_along(subjects)) {
    subject <- subjects[i]
    for (j in seq_along(tasks)) {
      task <- tasks[j]
      
      tryCatch({
        if (summary_type == "mean") {
          # Get mean patterns across gait cycle
          patterns <- get_mean_patterns(loco_data, subject, task, features)
          if (!is.null(patterns) && length(patterns) > 0) {
            feature_row <- sapply(features, function(f) {
              if (f %in% names(patterns)) {
                mean(patterns[[f]], na.rm = TRUE)
              } else {
                NA
              }
            })
            feature_matrix <- rbind(feature_matrix, feature_row)
            subject_labels <- c(subject_labels, subject)
            task_labels <- c(task_labels, task)
            row_metadata[[length(row_metadata) + 1]] <- list(
              subject = subject, task = task, summary_type = "mean"
            )
          }
          
        } else if (summary_type == "rom") {
          # Get range of motion values
          rom_result <- calculate_rom(loco_data, subject, task, features, by_cycle = FALSE)
          if (!is.null(rom_result) && length(rom_result) > 0) {
            feature_row <- sapply(features, function(f) {
              if (f %in% names(rom_result)) {
                rom_result[[f]]
              } else {
                NA
              }
            })
            feature_matrix <- rbind(feature_matrix, feature_row)
            subject_labels <- c(subject_labels, subject)
            task_labels <- c(task_labels, task)
            row_metadata[[length(row_metadata) + 1]] <- list(
              subject = subject, task = task, summary_type = "rom"
            )
          }
          
        } else if (summary_type == "full_cycle") {
          # Get full gait cycle data (flattened)
          cycles_result <- get_cycles(loco_data, subject, task, features)
          if (!is.null(cycles_result$data_3d)) {
            data_3d <- cycles_result$data_3d
            n_cycles <- dim(data_3d)[1]
            
            for (cycle in 1:n_cycles) {
              # Flatten the cycle data
              cycle_data <- as.vector(data_3d[cycle, , ])
              feature_matrix <- rbind(feature_matrix, cycle_data)
              subject_labels <- c(subject_labels, subject)
              task_labels <- c(task_labels, task)
              row_metadata[[length(row_metadata) + 1]] <- list(
                subject = subject, task = task, cycle = cycle, summary_type = "full_cycle"
              )
            }
          }
          
        } else if (summary_type == "peak_values") {
          # Extract peak values during gait cycle
          cycles_result <- get_cycles(loco_data, subject, task, features)
          if (!is.null(cycles_result$data_3d)) {
            data_3d <- cycles_result$data_3d
            
            # Calculate peaks across all cycles
            peak_values <- apply(data_3d, 3, function(feature_data) {
              max(feature_data, na.rm = TRUE)
            })
            min_values <- apply(data_3d, 3, function(feature_data) {
              min(feature_data, na.rm = TRUE)
            })
            
            # Combine peak and min values
            feature_row <- c(peak_values, min_values)
            feature_matrix <- rbind(feature_matrix, feature_row)
            subject_labels <- c(subject_labels, subject)
            task_labels <- c(task_labels, task)
            row_metadata[[length(row_metadata) + 1]] <- list(
              subject = subject, task = task, summary_type = "peak_values"
            )
          }
        }
        
      }, error = function(e) {
        warning(paste("Error processing", subject, task, ":", e$message))
      })
    }
  }
  
  if (is.null(feature_matrix) || nrow(feature_matrix) == 0) {
    stop("No valid data extracted for machine learning")
  }
  
  # Convert to data frame and set column names
  feature_df <- as.data.frame(feature_matrix)
  
  if (summary_type == "full_cycle") {
    # Create column names for flattened cycle data
    n_features <- length(features)
    n_phases <- ncol(feature_matrix) / n_features
    col_names <- c()
    for (f in features) {
      for (p in 1:n_phases) {
        col_names <- c(col_names, paste(f, "phase", p, sep = "_"))
      }
    }
    colnames(feature_df) <- col_names
  } else if (summary_type == "peak_values") {
    # Create column names for peak/min values
    peak_names <- paste(features, "max", sep = "_")
    min_names <- paste(features, "min", sep = "_")
    colnames(feature_df) <- c(peak_names, min_names)
  } else {
    colnames(feature_df) <- features
  }
  
  # Remove rows with missing values if requested
  if (remove_na) {
    complete_rows <- complete.cases(feature_df)
    if (sum(complete_rows) == 0) {
      stop("No complete cases found after removing missing values")
    }
    feature_df <- feature_df[complete_rows, ]
    subject_labels <- subject_labels[complete_rows]
    task_labels <- task_labels[complete_rows]
    row_metadata <- row_metadata[complete_rows]
  }
  
  # Normalize features if requested
  if (normalize) {
    feature_df <- as.data.frame(scale(feature_df))
  }
  
  # Create result object
  results <- list(
    features = feature_df,
    subjects = factor(subject_labels),
    tasks = factor(task_labels),
    metadata = row_metadata,
    summary_type = summary_type,
    normalized = normalize,
    n_samples = nrow(feature_df),
    n_features = ncol(feature_df),
    feature_names = colnames(feature_df),
    processing_info = list(
      subjects_included = subjects,
      tasks_included = tasks,
      original_features = features,
      timestamp = Sys.time()
    )
  )
  
  return(results)
}

#' Principal Component Analysis
#'
#' Performs PCA on biomechanical features for dimensionality reduction
#'
#' @param ml_data List, prepared ML data from prepare_ml_data
#' @param n_components Integer, number of components to retain (NULL for all)
#' @param variance_threshold Numeric, retain components explaining this proportion of variance
#' @return List containing PCA results
#'
#' @export
biomech_pca <- function(ml_data, n_components = NULL, variance_threshold = 0.95) {
  
  if (!"features" %in% names(ml_data)) {
    stop("Input must be prepared ML data with 'features' component")
  }
  
  feature_matrix <- ml_data$features
  
  # Perform PCA
  pca_result <- prcomp(feature_matrix, center = TRUE, scale. = TRUE)
  
  # Calculate variance explained
  variance_explained <- pca_result$sdev^2 / sum(pca_result$sdev^2)
  cumulative_variance <- cumsum(variance_explained)
  
  # Determine number of components to retain
  if (is.null(n_components)) {
    n_components <- which(cumulative_variance >= variance_threshold)[1]
    if (is.na(n_components)) {
      n_components <- length(variance_explained)
    }
  }
  
  # Extract principal components
  pca_scores <- pca_result$x[, 1:n_components, drop = FALSE]
  pca_loadings <- pca_result$rotation[, 1:n_components, drop = FALSE]
  
  # Create results
  results <- list(
    pca_object = pca_result,
    scores = pca_scores,
    loadings = pca_loadings,
    variance_explained = variance_explained[1:n_components],
    cumulative_variance = cumulative_variance[1:n_components],
    n_components = n_components,
    original_features = colnames(feature_matrix),
    subjects = ml_data$subjects,
    tasks = ml_data$tasks,
    metadata = ml_data$metadata,
    analysis_info = list(
      variance_threshold = variance_threshold,
      total_variance_explained = cumulative_variance[n_components],
      timestamp = Sys.time()
    )
  )
  
  return(results)
}

#' t-SNE Dimensionality Reduction
#'
#' Performs t-SNE for non-linear dimensionality reduction and visualization
#'
#' @param ml_data List, prepared ML data from prepare_ml_data
#' @param dims Integer, number of dimensions (default: 2)
#' @param perplexity Numeric, perplexity parameter (default: 30)
#' @param max_iter Integer, maximum iterations (default: 1000)
#' @param pca_init Logical, whether to initialize with PCA (default: TRUE)
#' @return List containing t-SNE results
#'
#' @export
biomech_tsne <- function(ml_data, dims = 2, perplexity = 30, max_iter = 1000, pca_init = TRUE) {
  
  if (!requireNamespace("Rtsne", quietly = TRUE)) {
    stop("Package 'Rtsne' needed for t-SNE analysis. Please install it with: install.packages('Rtsne')")
  }
  
  if (!"features" %in% names(ml_data)) {
    stop("Input must be prepared ML data with 'features' component")
  }
  
  feature_matrix <- as.matrix(ml_data$features)
  
  # Check perplexity constraint
  if (perplexity >= nrow(feature_matrix) / 3) {
    perplexity <- floor(nrow(feature_matrix) / 3)
    warning(paste("Perplexity adjusted to", perplexity, "due to sample size"))
  }
  
  # Perform t-SNE
  tryCatch({
    tsne_result <- Rtsne::Rtsne(
      feature_matrix, 
      dims = dims, 
      perplexity = perplexity,
      max_iter = max_iter,
      pca = pca_init,
      check_duplicates = FALSE
    )
    
    # Create results
    results <- list(
      embedding = tsne_result$Y,
      original_features = colnames(feature_matrix),
      subjects = ml_data$subjects,
      tasks = ml_data$tasks,
      metadata = ml_data$metadata,
      parameters = list(
        dims = dims,
        perplexity = perplexity,
        max_iter = max_iter,
        pca_init = pca_init
      ),
      analysis_info = list(
        n_samples = nrow(feature_matrix),
        n_features = ncol(feature_matrix),
        timestamp = Sys.time()
      )
    )
    
    return(results)
    
  }, error = function(e) {
    stop(paste("t-SNE analysis failed:", e$message))
  })
}

#' UMAP Dimensionality Reduction
#'
#' Performs UMAP for non-linear dimensionality reduction
#'
#' @param ml_data List, prepared ML data from prepare_ml_data
#' @param n_components Integer, number of dimensions (default: 2)
#' @param n_neighbors Integer, number of neighbors (default: 15)
#' @param min_dist Numeric, minimum distance (default: 0.1)
#' @return List containing UMAP results
#'
#' @export
biomech_umap <- function(ml_data, n_components = 2, n_neighbors = 15, min_dist = 0.1) {
  
  if (!requireNamespace("umap", quietly = TRUE)) {
    stop("Package 'umap' needed for UMAP analysis. Please install it with: install.packages('umap')")
  }
  
  if (!"features" %in% names(ml_data)) {
    stop("Input must be prepared ML data with 'features' component")
  }
  
  feature_matrix <- as.matrix(ml_data$features)
  
  # Configure UMAP
  umap_config <- umap::umap.defaults
  umap_config$n_components <- n_components
  umap_config$n_neighbors <- n_neighbors
  umap_config$min_dist <- min_dist
  
  # Perform UMAP
  tryCatch({
    umap_result <- umap::umap(feature_matrix, config = umap_config)
    
    # Create results
    results <- list(
      embedding = umap_result$layout,
      umap_object = umap_result,
      original_features = colnames(feature_matrix),
      subjects = ml_data$subjects,
      tasks = ml_data$tasks,
      metadata = ml_data$metadata,
      parameters = list(
        n_components = n_components,
        n_neighbors = n_neighbors,
        min_dist = min_dist
      ),
      analysis_info = list(
        n_samples = nrow(feature_matrix),
        n_features = ncol(feature_matrix),
        timestamp = Sys.time()
      )
    )
    
    return(results)
    
  }, error = function(e) {
    stop(paste("UMAP analysis failed:", e$message))
  })
}

#' K-means Clustering
#'
#' Performs k-means clustering on biomechanical data
#'
#' @param ml_data List, prepared ML data from prepare_ml_data
#' @param k Integer, number of clusters (NULL for automatic selection)
#' @param max_k Integer, maximum k to test for automatic selection (default: 10)
#' @param method Character, method for automatic k selection ("silhouette", "wss", "gap")
#' @param nstart Integer, number of random starts (default: 25)
#' @return List containing clustering results
#'
#' @export
biomech_kmeans <- function(ml_data, k = NULL, max_k = 10, method = "silhouette", nstart = 25) {
  
  if (!"features" %in% names(ml_data)) {
    stop("Input must be prepared ML data with 'features' component")
  }
  
  feature_matrix <- as.matrix(ml_data$features)
  
  # Determine optimal k if not specified
  if (is.null(k)) {
    if (requireNamespace("factoextra", quietly = TRUE)) {
      if (method == "silhouette") {
        k_analysis <- factoextra::fviz_nbclust(feature_matrix, kmeans, method = "silhouette", k.max = max_k)
        k <- which.max(k_analysis$data$y)
      } else if (method == "wss") {
        k_analysis <- factoextra::fviz_nbclust(feature_matrix, kmeans, method = "wss", k.max = max_k)
        # Find elbow point (simple heuristic)
        wss_values <- k_analysis$data$y
        diffs <- diff(wss_values)
        k <- which.min(diffs) + 1
      } else if (method == "gap") {
        k_analysis <- factoextra::fviz_nbclust(feature_matrix, kmeans, method = "gap_stat", k.max = max_k)
        k <- which.max(k_analysis$data$gap)
      }
    } else {
      # Simple silhouette method without factoextra
      sil_scores <- numeric(max_k - 1)
      for (i in 2:max_k) {
        km_temp <- kmeans(feature_matrix, centers = i, nstart = nstart)
        sil_temp <- cluster::silhouette(km_temp$cluster, dist(feature_matrix))
        sil_scores[i - 1] <- mean(sil_temp[, 3])
      }
      k <- which.max(sil_scores) + 1
    }
    
    if (is.null(k) || k < 2) {
      k <- 3  # Default fallback
      warning("Could not determine optimal k, using k=3")
    }
  }
  
  # Perform k-means clustering
  tryCatch({
    km_result <- kmeans(feature_matrix, centers = k, nstart = nstart)
    
    # Calculate silhouette scores
    sil_analysis <- cluster::silhouette(km_result$cluster, dist(feature_matrix))
    avg_silhouette <- mean(sil_analysis[, 3])
    
    # Calculate cluster characteristics
    cluster_summary <- data.frame(
      cluster = 1:k,
      size = km_result$size,
      within_ss = km_result$withinss,
      stringsAsFactors = FALSE
    )
    
    # Add subject and task information to clusters
    cluster_assignments <- data.frame(
      cluster = km_result$cluster,
      subject = ml_data$subjects,
      task = ml_data$tasks,
      stringsAsFactors = FALSE
    )
    
    # Create results
    results <- list(
      kmeans_object = km_result,
      cluster_assignments = cluster_assignments,
      cluster_summary = cluster_summary,
      silhouette_analysis = sil_analysis,
      avg_silhouette = avg_silhouette,
      k = k,
      centers = km_result$centers,
      total_ss = km_result$totss,
      between_ss = km_result$betweenss,
      within_ss = km_result$tot.withinss,
      original_features = colnames(feature_matrix),
      subjects = ml_data$subjects,
      tasks = ml_data$tasks,
      metadata = ml_data$metadata,
      analysis_info = list(
        method_used = ifelse(is.null(k), method, "user_specified"),
        nstart = nstart,
        timestamp = Sys.time()
      )
    )
    
    return(results)
    
  }, error = function(e) {
    stop(paste("K-means clustering failed:", e$message))
  })
}

#' Hierarchical Clustering
#'
#' Performs hierarchical clustering on biomechanical data
#'
#' @param ml_data List, prepared ML data from prepare_ml_data
#' @param method Character, linkage method ("ward.D2", "complete", "average", "single")
#' @param distance Character, distance metric ("euclidean", "manhattan", "correlation")
#' @param k Integer, number of clusters to cut tree (NULL for no cutting)
#' @return List containing hierarchical clustering results
#'
#' @export
biomech_hierarchical <- function(ml_data, method = "ward.D2", distance = "euclidean", k = NULL) {
  
  if (!"features" %in% names(ml_data)) {
    stop("Input must be prepared ML data with 'features' component")
  }
  
  feature_matrix <- as.matrix(ml_data$features)
  
  # Calculate distance matrix
  if (distance == "correlation") {
    dist_matrix <- as.dist(1 - cor(t(feature_matrix)))
  } else {
    dist_matrix <- dist(feature_matrix, method = distance)
  }
  
  # Perform hierarchical clustering
  tryCatch({
    hc_result <- hclust(dist_matrix, method = method)
    
    # Cut tree if k specified
    cluster_assignments <- NULL
    if (!is.null(k)) {
      clusters <- cutree(hc_result, k = k)
      cluster_assignments <- data.frame(
        cluster = clusters,
        subject = ml_data$subjects,
        task = ml_data$tasks,
        stringsAsFactors = FALSE
      )
      
      # Calculate silhouette scores for cut
      sil_analysis <- cluster::silhouette(clusters, dist_matrix)
      avg_silhouette <- mean(sil_analysis[, 3])
    } else {
      sil_analysis <- NULL
      avg_silhouette <- NULL
    }
    
    # Create results
    results <- list(
      hclust_object = hc_result,
      distance_matrix = dist_matrix,
      cluster_assignments = cluster_assignments,
      silhouette_analysis = sil_analysis,
      avg_silhouette = avg_silhouette,
      k = k,
      method = method,
      distance_metric = distance,
      original_features = colnames(feature_matrix),
      subjects = ml_data$subjects,
      tasks = ml_data$tasks,
      metadata = ml_data$metadata,
      analysis_info = list(
        n_samples = nrow(feature_matrix),
        timestamp = Sys.time()
      )
    )
    
    return(results)
    
  }, error = function(e) {
    stop(paste("Hierarchical clustering failed:", e$message))
  })
}

#' Support Vector Machine Classification
#'
#' Performs SVM classification on biomechanical data
#'
#' @param ml_data List, prepared ML data from prepare_ml_data
#' @param target Character, target variable ("subjects" or "tasks")
#' @param kernel Character, SVM kernel ("radial", "linear", "polynomial", "sigmoid")
#' @param cost Numeric, cost parameter (NULL for automatic tuning)
#' @param gamma Numeric, gamma parameter for RBF kernel (NULL for automatic)
#' @param cross_validation Integer, k-fold cross-validation (default: 5)
#' @return List containing SVM results
#'
#' @export
biomech_svm <- function(ml_data, target = "tasks", kernel = "radial", cost = NULL, 
                       gamma = NULL, cross_validation = 5) {
  
  if (!"features" %in% names(ml_data)) {
    stop("Input must be prepared ML data with 'features' component")
  }
  
  feature_matrix <- ml_data$features
  
  # Get target variable
  if (target == "tasks") {
    target_var <- ml_data$tasks
  } else if (target == "subjects") {
    target_var <- ml_data$subjects
  } else {
    stop("target must be 'tasks' or 'subjects'")
  }
  
  # Check if we have enough data for classification
  if (length(levels(target_var)) < 2) {
    stop("Target variable must have at least 2 levels for classification")
  }
  
  # Create training data
  train_data <- data.frame(
    target = target_var,
    feature_matrix,
    stringsAsFactors = FALSE
  )
  
  # Tune parameters if not specified
  if (is.null(cost) || is.null(gamma)) {
    tryCatch({
      tune_result <- tune(svm, target ~ ., data = train_data, kernel = kernel,
                         ranges = list(
                           cost = if (is.null(cost)) c(0.1, 1, 10, 100) else cost,
                           gamma = if (is.null(gamma) && kernel == "radial") c(0.001, 0.01, 0.1, 1) else gamma
                         ))
      best_cost <- tune_result$best.parameters$cost
      best_gamma <- tune_result$best.parameters$gamma
    }, error = function(e) {
      best_cost <- if (is.null(cost)) 1 else cost
      best_gamma <- if (is.null(gamma)) 1 / ncol(feature_matrix) else gamma
      warning("Parameter tuning failed, using defaults")
    })
  } else {
    best_cost <- cost
    best_gamma <- gamma
  }
  
  # Train SVM
  tryCatch({
    if (kernel == "radial") {
      svm_model <- svm(target ~ ., data = train_data, kernel = kernel, 
                      cost = best_cost, gamma = best_gamma, cross = cross_validation)
    } else {
      svm_model <- svm(target ~ ., data = train_data, kernel = kernel, 
                      cost = best_cost, cross = cross_validation)
    }
    
    # Make predictions
    predictions <- predict(svm_model, feature_matrix)
    
    # Calculate accuracy
    accuracy <- sum(predictions == target_var) / length(target_var)
    
    # Create confusion matrix
    confusion_matrix <- table(Predicted = predictions, Actual = target_var)
    
    # Calculate per-class metrics
    class_metrics <- data.frame(
      class = levels(target_var),
      precision = NA,
      recall = NA,
      f1_score = NA,
      stringsAsFactors = FALSE
    )
    
    for (i in seq_along(levels(target_var))) {
      class_name <- levels(target_var)[i]
      tp <- confusion_matrix[class_name, class_name]
      fp <- sum(confusion_matrix[class_name, ]) - tp
      fn <- sum(confusion_matrix[, class_name]) - tp
      
      precision <- ifelse(tp + fp > 0, tp / (tp + fp), 0)
      recall <- ifelse(tp + fn > 0, tp / (tp + fn), 0)
      f1 <- ifelse(precision + recall > 0, 2 * precision * recall / (precision + recall), 0)
      
      class_metrics$precision[i] <- precision
      class_metrics$recall[i] <- recall
      class_metrics$f1_score[i] <- f1
    }
    
    # Create results
    results <- list(
      svm_model = svm_model,
      predictions = predictions,
      accuracy = accuracy,
      confusion_matrix = confusion_matrix,
      class_metrics = class_metrics,
      cross_validation_accuracy = svm_model$tot.accuracy / 100,
      target_variable = target,
      parameters = list(
        kernel = kernel,
        cost = best_cost,
        gamma = best_gamma
      ),
      original_features = colnames(feature_matrix),
      subjects = ml_data$subjects,
      tasks = ml_data$tasks,
      metadata = ml_data$metadata,
      analysis_info = list(
        n_samples = nrow(feature_matrix),
        n_features = ncol(feature_matrix),
        n_classes = length(levels(target_var)),
        cross_validation_folds = cross_validation,
        timestamp = Sys.time()
      )
    )
    
    return(results)
    
  }, error = function(e) {
    stop(paste("SVM classification failed:", e$message))
  })
}

#' Random Forest Classification
#'
#' Performs Random Forest classification on biomechanical data
#'
#' @param ml_data List, prepared ML data from prepare_ml_data
#' @param target Character, target variable ("subjects" or "tasks")
#' @param ntree Integer, number of trees (default: 500)
#' @param mtry Integer, number of variables per split (NULL for automatic)
#' @param importance Logical, whether to calculate variable importance (default: TRUE)
#' @return List containing Random Forest results
#'
#' @export
biomech_random_forest <- function(ml_data, target = "tasks", ntree = 500, mtry = NULL, importance = TRUE) {
  
  if (!"features" %in% names(ml_data)) {
    stop("Input must be prepared ML data with 'features' component")
  }
  
  feature_matrix <- ml_data$features
  
  # Get target variable
  if (target == "tasks") {
    target_var <- ml_data$tasks
  } else if (target == "subjects") {
    target_var <- ml_data$subjects
  } else {
    stop("target must be 'tasks' or 'subjects'")
  }
  
  # Check if we have enough data for classification
  if (length(levels(target_var)) < 2) {
    stop("Target variable must have at least 2 levels for classification")
  }
  
  # Set default mtry if not specified
  if (is.null(mtry)) {
    mtry <- floor(sqrt(ncol(feature_matrix)))
  }
  
  # Create training data
  train_data <- data.frame(
    target = target_var,
    feature_matrix,
    stringsAsFactors = FALSE
  )
  
  # Train Random Forest
  tryCatch({
    rf_model <- randomForest(target ~ ., data = train_data, ntree = ntree, 
                           mtry = mtry, importance = importance)
    
    # Make predictions
    predictions <- predict(rf_model, feature_matrix)
    
    # Calculate accuracy
    accuracy <- sum(predictions == target_var) / length(target_var)
    
    # Create confusion matrix
    confusion_matrix <- table(Predicted = predictions, Actual = target_var)
    
    # Calculate per-class metrics
    class_metrics <- data.frame(
      class = levels(target_var),
      precision = NA,
      recall = NA,
      f1_score = NA,
      stringsAsFactors = FALSE
    )
    
    for (i in seq_along(levels(target_var))) {
      class_name <- levels(target_var)[i]
      tp <- confusion_matrix[class_name, class_name]
      fp <- sum(confusion_matrix[class_name, ]) - tp
      fn <- sum(confusion_matrix[, class_name]) - tp
      
      precision <- ifelse(tp + fp > 0, tp / (tp + fp), 0)
      recall <- ifelse(tp + fn > 0, tp / (tp + fn), 0)
      f1 <- ifelse(precision + recall > 0, 2 * precision * recall / (precision + recall), 0)
      
      class_metrics$precision[i] <- precision
      class_metrics$recall[i] <- recall
      class_metrics$f1_score[i] <- f1
    }
    
    # Extract variable importance if calculated
    var_importance <- NULL
    if (importance) {
      var_importance <- data.frame(
        feature = rownames(rf_model$importance),
        mean_decrease_accuracy = rf_model$importance[, "MeanDecreaseAccuracy"],
        mean_decrease_gini = rf_model$importance[, "MeanDecreaseGini"],
        stringsAsFactors = FALSE
      )
      var_importance <- var_importance[order(var_importance$mean_decrease_accuracy, decreasing = TRUE), ]
    }
    
    # Create results
    results <- list(
      rf_model = rf_model,
      predictions = predictions,
      accuracy = accuracy,
      confusion_matrix = confusion_matrix,
      class_metrics = class_metrics,
      variable_importance = var_importance,
      oob_error = rf_model$err.rate[ntree, "OOB"],
      target_variable = target,
      parameters = list(
        ntree = ntree,
        mtry = mtry
      ),
      original_features = colnames(feature_matrix),
      subjects = ml_data$subjects,
      tasks = ml_data$tasks,
      metadata = ml_data$metadata,
      analysis_info = list(
        n_samples = nrow(feature_matrix),
        n_features = ncol(feature_matrix),
        n_classes = length(levels(target_var)),
        timestamp = Sys.time()
      )
    )
    
    return(results)
    
  }, error = function(e) {
    stop(paste("Random Forest classification failed:", e$message))
  })
}