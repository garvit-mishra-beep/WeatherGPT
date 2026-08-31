package com.weathergpt.core.result

import com.weathergpt.core.error.AppError

/**
 * Standard sealed result container for asynchronous data operations.
 */
sealed interface ResultState<out T> {

    /**
     * Initial idle state before an operation begins.
     */
    data object Idle : ResultState<Nothing>

    /**
     * In-flight loading state.
     */
    data object Loading : ResultState<Nothing>

    /**
     * Successful completion with strongly-typed data.
     */
    data class Success<out T>(val data: T) : ResultState<T>

    /**
     * Failed execution with a domain [AppError].
     */
    data class Error(val error: AppError) : ResultState<Nothing>

    val isSuccess: Boolean
        get() = this is Success

    val isError: Boolean
        get() = this is Error

    val isLoading: Boolean
        get() = this is Loading

    fun getOrNull(): T? = when (this) {
        is Success -> data
        else -> null
    }
}
