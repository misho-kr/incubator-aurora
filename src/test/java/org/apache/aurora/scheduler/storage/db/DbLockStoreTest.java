/**
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.aurora.scheduler.storage.db;

import java.io.IOException;
import java.util.Set;

import com.google.common.base.Optional;
import com.google.common.collect.ImmutableSet;
import com.google.inject.Guice;
import com.google.inject.Injector;
import com.twitter.common.inject.Bindings;

import org.apache.aurora.gen.JobKey;
import org.apache.aurora.gen.Lock;
import org.apache.aurora.gen.LockKey;
import org.apache.aurora.scheduler.base.JobKeys;
import org.apache.aurora.scheduler.storage.Storage;
import org.apache.aurora.scheduler.storage.Storage.MutableStoreProvider;
import org.apache.aurora.scheduler.storage.Storage.MutateWork;
import org.apache.aurora.scheduler.storage.Storage.StorageException;
import org.apache.aurora.scheduler.storage.Storage.StoreProvider;
import org.apache.aurora.scheduler.storage.Storage.Work.Quiet;
import org.apache.aurora.scheduler.storage.entities.ILock;
import org.apache.aurora.scheduler.storage.entities.ILockKey;
import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

public class DbLockStoreTest {

  private DbStorage storage;

  private void assertLocks(final ILock... expected) {
    assertEquals(
        ImmutableSet.<ILock>builder().add(expected).build(),
        storage.consistentRead(new Quiet<Set<ILock>>() {
          @Override
          public Set<ILock> apply(Storage.StoreProvider storeProvider) {
            return storeProvider.getLockStore().fetchLocks();
          }
        }));
  }

  private Optional<ILock> getLock(final ILockKey key) {
    return storage.consistentRead(new Quiet<Optional<ILock>>() {
      @Override
      public Optional<ILock> apply(StoreProvider storeProvider) {
        return storeProvider.getLockStore().fetchLock(key);
      }
    });
  }

  private void saveLocks(final ILock... locks) {
    storage.write(new MutateWork.Quiet<Void>() {
      @Override
      public Void apply(MutableStoreProvider storeProvider) {
        for (ILock lock : locks) {
          storeProvider.getLockStore().saveLock(lock);
        }
        return null;
      }
    });
  }

  private void removeLocks(final ILock... locks) {
    storage.write(new MutateWork.Quiet<Void>() {
      @Override
      public Void apply(MutableStoreProvider storeProvider) {
        for (ILock lock : locks) {
          storeProvider.getLockStore().removeLock(lock.getKey());
        }
        return null;
      }
    });
  }

  private static ILock makeLock(JobKey key) {
    return ILock.build(new Lock()
      .setKey(LockKey.job(key))
      .setToken("lock1")
      .setUser("testUser")
      .setMessage("Test message")
      .setTimestampMs(12345L));
  }

  @Before
  public void setUp() throws IOException {
    Injector injector = Guice.createInjector(DbModule.testModule(Bindings.KeyFactory.PLAIN));
    storage = injector.getInstance(DbStorage.class);
    storage.prepare();
  }

  @Test
  public void testLocks() throws Exception {
    assertLocks();

    String role = "testRole";
    String env = "testEnv";
    String job1 = "testJob1";
    String job2 = "testJob2";

    ILock lock1 = makeLock(JobKeys.from(role, env, job1).newBuilder());
    ILock lock2 = makeLock(JobKeys.from(role, env, job2).newBuilder());

    saveLocks(lock1, lock2);
    assertLocks(lock1, lock2);
    removeLocks(lock1);

    assertLocks(lock2);
  }

  @Test
  public void testRepeatedWrite() throws Exception {
    assertLocks();

    String role = "testRole";
    String env = "testEnv";
    String job = "testJob";

    ILock lock = makeLock(JobKeys.from(role, env, job).newBuilder());

    saveLocks(lock);
    try {
      saveLocks(lock);
      fail("saveLock should have failed unique constraint check.");
    } catch (StorageException e) {
      // expected
    }

    assertLocks(lock);
  }

  @Test
  public void testExistingJobKey() throws Exception {
    String role = "testRole";
    String env = "testEnv";
    String job = "testJob";

    ILock lock = makeLock(JobKeys.from(role, env, job).newBuilder());

    saveLocks(lock);
    removeLocks(lock);
    saveLocks(lock);

    assertLocks(lock);
  }

  @Test
  public void testGetLock() throws Exception {
    assertLocks();

    String role = "testRole";
    String env = "testEnv";
    String job = "testJob";

    final ILock lock = makeLock(JobKeys.from(role, env, job).newBuilder());

    assertEquals(Optional.absent(), getLock(lock.getKey()));

    saveLocks(lock);
    assertEquals(Optional.<ILock>of(lock), getLock(lock.getKey()));
  }

  @Test
  public void testDeleteAllLocks() throws Exception {
    assertLocks();

    String role = "testRole";
    String env = "testEnv";
    String job1 = "testJob1";
    String job2 = "testJob2";

    ILock lock1 = makeLock(JobKeys.from(role, env, job1).newBuilder());
    ILock lock2 = makeLock(JobKeys.from(role, env, job2).newBuilder());

    saveLocks(lock1, lock2);
    assertLocks(lock1, lock2);

    storage.write(new MutateWork.Quiet<Void>() {
      @Override
      public Void apply(MutableStoreProvider storeProvider) {
        storeProvider.getLockStore().deleteLocks();
        return null;
      }
    });

    assertLocks();
  }
}
