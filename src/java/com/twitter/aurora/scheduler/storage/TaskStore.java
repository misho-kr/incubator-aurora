package com.twitter.aurora.scheduler.storage;

import java.util.Set;

import com.google.common.base.Supplier;
import com.google.common.collect.ImmutableSet;

import com.twitter.aurora.gen.ScheduledTask;
import com.twitter.aurora.gen.TaskQuery;
import com.twitter.aurora.gen.TwitterTaskInfo;
import com.twitter.common.base.Closure;

/**
 * Stores all tasks configured with the scheduler.
 */
public interface TaskStore {

  /**
   * Fetches a read-only view of tasks matching a query and filters.
   *
   * @deprecated Use {@link #fetchTaskIds(Supplier)}.
   * @param query Query to identify tasks with.
   * @return A read-only view of matching tasks.
   */
  @Deprecated
  ImmutableSet<ScheduledTask> fetchTasks(TaskQuery query);

  /**
   * Fetches a read-only view of tasks matching a query and filters. Intended for use with a
   * {@link com.twitter.aurora.scheduler.base.Query.Builder}.
   *
   * @param querySupplier Supplier of the query to identify tasks with.
   * @return A read-only view of matching tasks.
   */
  ImmutableSet<ScheduledTask> fetchTasks(Supplier<TaskQuery> querySupplier);

  /**
   * Convenience method to execute a query and only retrieve the IDs of the matching tasks.
   *
   * @deprecated Use {@link #fetchTaskIds(Supplier)}.
   * @param query Query to identify tasks with.
   * @return IDs of the matching tasks.
   */
  @Deprecated
  Set<String> fetchTaskIds(TaskQuery query);

  /**
   * Convenience method to execute a query and only retrieve the IDs of the matching tasks.
   *
   * @param querySupplier Supplier of the query to identify tasks with.
   * @return IDs of the matching tasks.
   */
  Set<String> fetchTaskIds(Supplier<TaskQuery> querySupplier);

  public interface Mutable extends TaskStore {
    /**
     * Saves tasks to the store.  Tasks are copied internally, meaning that the tasks are stored in
     * the state they were in when the method is called, and further object modifications will not
     * affect the tasks.  If any of the tasks already exist in the store, they will be overwritten
     * by the supplied {@code newTasks}.
     *
     * @param tasks Tasks to add.
     */
    void saveTasks(Set<ScheduledTask> tasks);

    /**
     * Removes all tasks from the store.
     */
    void deleteAllTasks();

    /**
     * Deletes specific tasks from the store.
     *
     * @param taskIds IDs of tasks to delete.
     */
    void deleteTasks(Set<String> taskIds);

    /**
     * Offers temporary mutable access to tasks.  If a task ID is not found, it will be silently
     * skipped, and no corresponding task will be returned.
     *
     * @param query Query to match tasks against.
     * @param mutator The mutate operation.
     * @return Immutable copies of only the tasks that were mutated.
     */
    ImmutableSet<ScheduledTask> mutateTasks(TaskQuery query, Closure<ScheduledTask> mutator);

    /**
     * Rewrites a task's configuration in-place.
     * <p>
     * <b>WARNING</b>: this is a dangerous operation, and should not be used without exercising
     * great care.  This feature should be used as a last-ditch effort to rewrite things that
     * the scheduler otherwise can't (e.g. {@link TwitterTaskInfo#thermosConfig}) rewrite in a
     * controlled/tested backfill operation.
     *
     * @param taskId ID of the task to alter.
     * @param taskConfiguration Configuration object to swap with the existing task's configuration.
     * @return {@code true} if the modification took effect, or {@code false} if the task does not
     *         exist in the store.
     */
    boolean unsafeModifyInPlace(String taskId, TwitterTaskInfo taskConfiguration);
  }
}