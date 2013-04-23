package com.twitter.mesos.scheduler.configuration;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Objects;
import com.google.common.base.Preconditions;

import com.twitter.mesos.gen.JobConfiguration;
import com.twitter.mesos.scheduler.configuration.ConfigurationManager.TaskDescriptionException;

/**
 * Wrapper for a configuration that has been fully-parsed and populated with defaults.
 * TODO(wfarner): Rename this to SanitizedConfiguration.
 */
public final class ParsedConfiguration {

  private final JobConfiguration parsed;

  @VisibleForTesting
  public ParsedConfiguration(JobConfiguration parsed) throws TaskDescriptionException {
    this.parsed = parsed;
  }

  /**
   * Wraps an unparsed job configuration.
   *
   * @param unparsed Unparsed configuration to parse/populate and wrap.
   * @return A wrapper containing the parsed configuration.
   * @throws TaskDescriptionException If the configuration is invalid.
   */
  public static ParsedConfiguration fromUnparsed(JobConfiguration unparsed)
      throws TaskDescriptionException {

    Preconditions.checkNotNull(unparsed);
    return new ParsedConfiguration(ConfigurationManager.validateAndPopulate(unparsed));
  }

  public JobConfiguration get() {
    return parsed;
  }

  @Override
  public boolean equals(Object o) {
    if (!(o instanceof ParsedConfiguration)) {
      return false;
    }

    ParsedConfiguration other = (ParsedConfiguration) o;

    return Objects.equal(parsed, other.parsed);
  }

  @Override
  public int hashCode() {
    return parsed.hashCode();
  }

  @Override
  public String toString() {
    return parsed.toString();
  }
}